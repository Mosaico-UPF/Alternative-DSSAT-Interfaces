const fs = require('fs');
const path = require('path');
const EvaluateOutput = require('./evaluateOutput');
const { readTFile } = require('./tfiles');
const Output = require('./output');
const { convertToISODate } = require('./utils');

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
        throw new Error("No data found in the OUT file.");
    }

    const experiment = parsedData[0].experiment;
    const resultMap = {};

    // Populate simulated from parsed OUT data (assuming refactored to unified model)
    for (const record of parsedData) {
        const trno = record.treatmentNumber;
        const runName = record.run || `Treatment_${trno}`;
        if (!resultMap[trno]) {
            resultMap[trno] = {
                run: runName,
                treatmentNumber: trno,
                experiment: experiment,
                fileType: 'MERGED',
                simulated: record.simulated || {},
                measuredFinal: {},
                measuredTimeSeries: {}
            };
        } else {
            Object.assign(resultMap[trno].simulated, record.simulated);
        }
    }

    // Measured data from Evaluate.OUT
    const evaluate = new EvaluateOutput(fs, baseDir, { load: () => [] });
    const evaluateData = evaluate.read(crop, 'Evaluate.OUT').results || [];
    for (const record of evaluateData) {
        const excode = record.EXCODE?.value?.toUpperCase();
        if (excode !== experiment.toUpperCase()) continue;
        const trno = record.TRNO?.value?.toString();
        if (!resultMap[trno]) {
            resultMap[trno] = {
                run: `Treatment_${trno}`,
                treatmentNumber: trno,
                experiment: excode,
                fileType: 'MERGED',
                simulated: {},
                measuredFinal: {},
                measuredTimeSeries: {}
            };
        }
        for (const [key, entry] of Object.entries(record)) {
            if (entry.type === 'combined') {
                resultMap[trno].simulated[key] = { values: entry.simulated, dates: [] }; // Assuming no dates in Evaluate; add if needed
                resultMap[trno].measuredFinal[key] = entry.measured;
            }
        }
    }

    // Measured time-series from T file
    const tFile = findFileByExtension(cropFolder, experiment, 'timeSeries', crop);
    if (tFile) {
        const tData = await new Promise(resolve => readTFile(crop, tFile, resolve));
        for (const runData of tData || []) {
            const trno = runData.treatmentNumber;
            if (!resultMap[trno]) {
                resultMap[trno] = {
                    run: runData.run,
                    treatmentNumber: trno,
                    experiment: runData.experiment || experiment,
                    fileType: 'MERGED',
                    simulated: {},
                    measuredFinal: {},
                    measuredTimeSeries: runData.measuredTimeSeries || {}
                };
            } else {
                Object.assign(resultMap[trno].measuredTimeSeries, runData.measuredTimeSeries);
            }
        }
    }

    // Measured final from A file
    const aFile = findFileByExtension(cropFolder, experiment, 'summary', crop);
    if (aFile) {
        const aPath = path.join(cropFolder, aFile);
        const aData = parseAFile(aPath);
        for (const [trno, values] of Object.entries(aData)) {
            if (!resultMap[trno]) {
                resultMap[trno] = {
                    run: `Treatment_${trno}`,
                    treatmentNumber: trno,
                    experiment: experiment,
                    fileType: 'MERGED',
                    simulated: {},
                    measuredFinal: {},
                    measuredTimeSeries: {}
                };
            }
            for (const [cde, val] of Object.entries(values)) {
                resultMap[trno].measuredFinal[cde] = val; // Single value
            }
        }
    }

    // For consistency, ensure measuredFinal uses {value: X} if not already
    Object.values(resultMap).forEach(run => {
        for (const [cde, val] of Object.entries(run.measuredFinal)) {
            if (typeof val !== 'object') {
                run.measuredFinal[cde] = { value: val };
            }
        }
    });

    return Object.values(resultMap);
}

module.exports = { loadSimVsObsFromOutFile };