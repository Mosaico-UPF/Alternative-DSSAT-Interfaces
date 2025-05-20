const fs = require('fs');
const path = require('path');
const cde = require('./cde');

function parseTFile(filePath) {
    const data = fs.readFileSync(filePath, 'utf8');
    const lines = data.split(/[\r\n]+/g);

    let experiment = "Unknown";
    let runs = [];
    let headers = [];
    let currentHeaders = [];
    let parsingData = false;

    const DATE_COL = 'DATE';
    const TRNO_COL = 'TRNO';
    const EXCLUDED_COLUMNS = [TRNO_COL, DATE_COL];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (line.startsWith('*EXP.DATA (T):')) {
            experiment = line.split('*EXP.DATA (T):')[1].trim();
            continue;
        }

        if (line.startsWith('@')) {
            currentHeaders = line.slice(1).trim().split(/\s+/);
            headers = currentHeaders.filter(h => !EXCLUDED_COLUMNS.includes(h));
            parsingData = true;
            continue;
        }

        if (parsingData && line.length > 0 && !line.startsWith('!')) {
            const values = line.split(/\s+/);
            const runNumber = values[currentHeaders.indexOf(TRNO_COL)];
            const date = values[currentHeaders.indexOf(DATE_COL)];
            const day = convertYYDDDToDate(date); 
            


            const runValues = [];
            headers.forEach(header => {
                const valueIndex = currentHeaders.indexOf(header);
                if (valueIndex !== -1 && values[valueIndex] !== undefined) {
                    const value = values[valueIndex];
                    if (value !== '-99') {
                        runValues.push({
                            cde: header,
                            values: [parseFloat(value)]
                        });
                    }
                }
            });

            runs.push({
                run: runNumber,
                runName: generateRunName(experiment, runNumber),
                experiment: experiment,
                day: day,
                values: runValues
            });
        }
    }

    return runs;
}

function convertYYDDDToDate(yyddd) {
    if (!yyddd || yyddd === '-99') return null;

    const num = parseInt(yyddd);
    const yy = Math.floor(num / 1000);
    const doy = num % 1000;
    const year = yy >= 40 ? 1900 + yy : 2000 + yy;

    const date = new Date(year, 0);
    date.setDate(date.getDate() + doy - 1); 
    return date.toISOString().split('T')[0];
}

function generateRunName(experiment, runNumber) {
    const yearMatch = experiment.match(/\d{2}/);
    const year = yearMatch ? yearMatch[0] : "YY";

    const treatmentInfo = experiment.split(',').map(s => s.trim());

    let cultivars = [];
    if (treatmentInfo[0].includes('&')) {
        cultivars = treatmentInfo[0].split('&').map(s => s.trim());
    } else {
        cultivars = [treatmentInfo[0]]; 
    }

    const treatmentType = treatmentInfo.length > 1 ? treatmentInfo[1] : "Unknown";

    const cultivar = (cultivars[runNumber - 1] || `Run ${runNumber}`).replace(/IUAM\d{4}SB\s*/, '');

    return `${year}-${cultivar} ${treatmentType} (${runNumber})`;
}

function readTFile(crop, filename, callback) {
    const folderPath = path.join('C:/DSSAT48', crop);
    const tFilePath = path.join(folderPath, filename);
    
    if (!fs.existsSync(tFilePath)) {
        console.error(`File not found: ${tFilePath}`);
        callback(null);
        return;
    }
    
    try {
        const parsedData = parseTFile(tFilePath);
        callback(parsedData);
    } catch (error) {
        console.error(`Error parsing TFile: ${tFilePath}`, error.message);
        callback(null);
    }
}

module.exports = { readTFile };