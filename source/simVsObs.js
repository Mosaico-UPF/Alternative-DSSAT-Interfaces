const fs = require('fs');
const path = require('path');
const EvaluateOutput = require('./evaluateOutput');
const { readTFile } = require('./tfiles');
const Output = require('./output');

function parseAFile(filePath) {
    const data = fs.readFileSync(filePath, 'utf8');
    const lines = data.split(/\r?\n/);
    const results = {};
    let headers = [];

    for (const line of lines) {
        if (line.startsWith('@')) {
            headers = line.slice(1).trim().split(/\s+/);
        } else if (line.trim() !== '' && !line.startsWith('!')) {
            const values = line.trim().split(/\s+/);
            const trno = values[0];
            if (!results[trno]) results[trno] = {};
            headers.forEach((h, idx) => {
                const val = values[idx];
                if (val !== '-99') results[trno][h] = parseFloat(val);
            });
        }
    }
    return results;
}

const CROP_EXTENSIONS = {
    'Alfalfa': { timeSeries: '.alt', summary: '.ala' },
    'Aroid': { timeSeries: '.art', summary: '.ara' },
    'Barley': { timeSeries: '.bat', summary: '.baa' },
    'Dry bean': { timeSeries: '.bnt', summary: '.bna' },
    'Broad leaf weeds': { timeSeries: '.bwt', summary: '.bwa' },
    'Cotton': { timeSeries: '.cot', summary: '.coa' },
    'Cassava': { timeSeries: '.cst', summary: '.csa' },
    'Fallow': { timeSeries: '.fat', summary: '.faa' },
    'Grass-weeds': { timeSeries: '.gwt', summary: '.gwa' },
    'Millet': { timeSeries: '.mlt', summary: '.mla' },
    'Maize': { timeSeries: '.mzt', summary: '.mza' },
    'Peanut': { timeSeries: '.pnt', summary: '.pna' },
    'Potato': { timeSeries: '.ptt', summary: '.pta' },
    'Rice': { timeSeries: '.rit', summary: '.ria' },
    'Soybean': { timeSeries: '.sbt', summary: '.sba' },
    'Sugar cane': { timeSeries: '.sct', summary: '.sca' },
    'Sorghum': { timeSeries: '.sgt', summary: '.sga' },
    'Shrubs': { timeSeries: '.stt', summary: '.sta' },
    'Wheat': { timeSeries: '.wht', summary: '.wha' }
};

function findFileByExtension(cropFolder, experiment, fileType, crop) {
    const ext = CROP_EXTENSIONS[crop]?.[fileType] || (fileType === 'timeSeries' ? '.T' : '.A');
    const fileName = `${experiment}${ext}`;
    const filePath = path.join(cropFolder, fileName);
    return fs.existsSync(filePath) ? fileName : null;
}

async function loadSimVsObsFromOutFile(crop, outFile) {
    const baseDir = path.resolve('C:/DSSAT48');
    const cropFolder = path.join(baseDir, crop);
    const outputParser = new Output(fs);
    const parsedData = outputParser.read(baseDir + '/', crop, outFile);

    if (!parsedData || parsedData.length === 0) {
        //console.error(`No data found in OUT file: ${outFile}`);
        throw new Error("No data found in the OUT file.");
    }

    const experiment = parsedData[0].experiment;
    const trnoMap = {};

    // Simulated data from .OUT
    for (const record of parsedData) {
        const trno = record.treatmentNumber;
        const runName = record.run || `Treatment_${trno}`; // Fallback run name
        if (!trnoMap[trno]) {
            trnoMap[trno] = {
                runName: runName,
                simulated: {},
                measured_final: {},
                measured_time_series: [],
                excode: experiment,
            };
        }
        for (const variable of record.values) {
            const cde = variable.cde;
            const values = variable.values;
            trnoMap[trno].simulated[cde] = values.map(v => parseFloat(v));
        }
    }

    // Measured data from Evaluate.OUT
    const evaluate = new EvaluateOutput(fs, baseDir, { load: () => [] });
    const evaluateData = evaluate.read(crop, 'Evaluate.OUT').results || [];
    for (const record of evaluateData) {
        const excode = record.EXCODE?.value?.toUpperCase();
        if (excode !== experiment.toUpperCase()) {
            continue;
        }
        const trno = record.TRNO?.value?.toString();
        if (!trnoMap[trno]) {
            trnoMap[trno] = {
                runName: `Treatment_${trno}`,
                simulated: {},
                measured_final: {},
                measured_time_series: [],
                excode: excode,
            };
        }
        for (const [key, entry] of Object.entries(record)) {
            if (entry.type === 'combined') {
                trnoMap[trno].simulated[key] = entry.simulated;
                trnoMap[trno].measured_final[key] = entry.measured;
            }
        }
    }

    
    const tFile = findFileByExtension(cropFolder, experiment, 'timeSeries', crop);
    if (tFile) {
        const tData = await new Promise(resolve => readTFile(crop, tFile, resolve));
        for (const row of tData || []) {
            const trno = row.run;
            if (!trnoMap[trno]) {
                trnoMap[trno] = {
                    runName: row.runName || row.run || `Treatment_${trno}`,
                    simulated: {},
                    measured_final: {},
                    measured_time_series: [],
                    excode: row.experiment || experiment,
                };
            }
            const values = {};
            row.values.forEach(v => {
                const cde = v.cde;
                const val = v.values[0];
                if (!trnoMap[trno]._observed_series_by_var) {
                    trnoMap[trno]._observed_series_by_var = {};
                }
                if (!trnoMap[trno]._observed_series_by_var[cde]) {
                    trnoMap[trno]._observed_series_by_var[cde] = {
                        values: [],
                        dates: []
                    };
                }
                trnoMap[trno]._observed_series_by_var[cde].values.push(val);
                trnoMap[trno]._observed_series_by_var[cde].dates.push(row.day);

                values[cde] = val;
            });
            trnoMap[trno].measured_time_series.push({ date: row.day, ...values });

        }
    }

    const aFile = findFileByExtension(cropFolder, experiment, 'summary', crop);
    if (aFile) {
        const aPath = path.join(cropFolder, aFile);
        const aData = parseAFile(aPath);
        for (const [trno, values] of Object.entries(aData)) {
            if (!trnoMap[trno]) {
                trnoMap[trno] = {
                    runName: `Treatment_${trno}`,
                    simulated: {},
                    measured_final: {},
                    measured_time_series: [],
                    excode: experiment,
                };
            }
            Object.assign(trnoMap[trno].measured_final, values);
        }
    }

    // Create a map keyed by runName for frontend compatibility
    const runNameMap = {};
    for (const [trno, data] of Object.entries(trnoMap)) {
        if (data.runName) {
            runNameMap[data.runName] = data;
        }
    }

    const formattedResults = [];

for (const [trno, data] of Object.entries(trnoMap)) {
    const run = data.runName || trno;
    const formatted = {
        run,
        experiment: data.excode,
        file_type: 'out',
        values: []
    };

    // Simulated
    for (const [cde, values] of Object.entries(data.simulated)) {
        formatted.values.push({
            cde,
            values,
            type: 'simulated'
        });
    }

    // Measured (final)
    for (const [cde, val] of Object.entries(data.measured_final)) {
        formatted.values.push({
            cde,
            values: Array.isArray(val) ? val : [val],
            type: 'measured'
        });
    }

    // Measured (time series with x_calendar)
    const obsSeries = data._observed_series_by_var || {};
    for (const [cde, obj] of Object.entries(obsSeries)) {
        formatted.values.push({
            cde,
            values: obj.values,
            x_calendar: obj.dates,
            type: 'measured'
        });
    }

    formattedResults.push(formatted);
}

    const result = { ...trnoMap, ...runNameMap };
    //console.log(`Sim-vs-Obs response: ${JSON.stringify(result, null, 2)}`);
    return result;
}

module.exports = { loadSimVsObsFromOutFile };