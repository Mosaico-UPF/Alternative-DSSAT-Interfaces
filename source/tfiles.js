// tfiles.js
const fs = require('fs');
const path = require('path');
const { convertToISODate } = require('./utils');
const Xfile = require('./xfile'); // Import Xfile class

function parseTFile(filePath) {
    const data = fs.readFileSync(filePath, 'utf8');
    const lines = data.split(/[\r\n]+/g);

    let experiment = "Unknown";
    const runsMap = {};
    let headers = [];
    let currentHeaders = [];
    let parsingData = false;
    let yearFromDates = null;

    const DATE_COL = 'DATE';
    const TRNO_COL = 'TRNO';
    const EXCLUDED_COLUMNS = [TRNO_COL, DATE_COL];

    const fileName = path.basename(filePath);
    const baseDir = path.dirname(filePath);
    const experimentCode = fileName.split('.')[0]; // e.g., UFGA8201
    const crop = path.basename(path.dirname(filePath)); // e.g., Maize

    // Load treatment names from corresponding X file
    let trnoToName = {};
    try {
        const xfile = new Xfile(fs);
        const xFilePath = path.join(baseDir, `${experimentCode}.MZX`); // Assume X file has .MZX extension
        if (fs.existsSync(xFilePath)) {
            const treatments = xfile.getTreatments(path.dirname(baseDir) + '/', crop, '/', [fileName.replace('.MZT', '.MZX')]);
            treatments.forEach(t => {
                trnoToName[t.N_Level] = t.TNAME_Description;
            });
        }
    } catch (error) {
        console.error(`Error loading treatments for ${experimentCode}:`, error.message);
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        const expMatch = line.match(/^\*EXP\.?\s*DATA\s*\(T\):\s*(.*)$/i);
        if (expMatch) {
            experiment = expMatch[1].trim();
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
            const trno = values[currentHeaders.indexOf(TRNO_COL)];
            const dateYYDDD = values[currentHeaders.indexOf(DATE_COL)];
            const date = convertToISODate(dateYYDDD);

            if (!yearFromDates && dateYYDDD && dateYYDDD !== '-99') {
                const num = parseInt(dateYYDDD, 10);
                if (!isNaN(num)) {
                    const yy = Math.floor(num / 1000);
                    yearFromDates = (yy >= 40 ? 1900 + yy : 2000 + yy);
                }
            }

            if (!runsMap[trno]) {
                const runNum = parseInt(trno, 10);
                // Use treatment name from X file if available, else fall back
                const treatmentName = trnoToName[trno] || `Treatment_${trno}`;
                const runLabel = generateRunName(experiment, runNum, fileName, yearFromDates, treatmentName);

                runsMap[trno] = {
                    run: runLabel,
                    runName: runLabel,
                    treatmentNumber: trno,
                    experiment: experiment,
                    fileType: 'T',
                    simulated: {},
                    measuredFinal: {},
                    measuredTimeSeries: {}
                };
            }

            headers.forEach(header => {
                const valueIndex = currentHeaders.indexOf(header);
                if (valueIndex !== -1 && values[valueIndex] !== undefined) {
                    const value = values[valueIndex];
                    if (value !== '-99' && date) {
                        const val = parseFloat(value);
                        if (!runsMap[trno].measuredTimeSeries[header]) {
                            runsMap[trno].measuredTimeSeries[header] = { values: [], dates: [] };
                        }
                        runsMap[trno].measuredTimeSeries[header].values.push(val);
                        runsMap[trno].measuredTimeSeries[header].dates.push(date);
                    }
                }
            });
        }
    }

    Object.values(runsMap).forEach(run => {
        Object.values(run.measuredTimeSeries).forEach(ts => {
            const sortedIndices = ts.dates.map((_, idx) => idx)
                .sort((a, b) => new Date(ts.dates[a]) - new Date(ts.dates[b]));
            ts.dates = sortedIndices.map(i => ts.dates[i]);
            ts.values = sortedIndices.map(i => ts.values[i]);
        });
    });

    return Object.values(runsMap);
}

function smartCase(s) {
    if (!s) return s;
    if (s === s.toUpperCase()) {
        return s.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
    }
    return s;
}

function generateRunName(experiment, runNumber, fileName = "", yearFromDates = null, treatmentName = null) {
    const num = parseInt(runNumber, 10) || 0;

    // Prefer treatmentName from X file if provided
    if (treatmentName) {
        const prettyName = smartCase(treatmentName);
        return `${prettyName} (${num})`;
    }

    // Fallback to existing logic
    const baseExp = (experiment || "").trim();
    const cleaned = baseExp.replace(/^[A-Za-z]{4}\d{2,4}[A-Za-z]{0,3}\s*/, '').trim();
    const segments = cleaned.split(',').map(s => s.trim()).filter(Boolean);
    const primary = segments[0] || '';
    const secondary = segments[1] || '';

    let chosen = '';
    if (primary.includes('&') || /\band\b/i.test(primary)) {
        const cvParts = primary.split(/\s*&\s*|\s+\band\s+/i).map(s => s.trim()).filter(Boolean);
        chosen = cvParts[(num - 1) % cvParts.length] || cvParts[0] || '';
    } else {
        chosen = primary || '';
    }

    if (!chosen && !secondary) {
        chosen = `Run ${num}`;
    }

    let yearStr = yearFromDates ? String(yearFromDates) : '';
    if (!yearStr && fileName) {
        const m = fileName.match(/[A-Za-z]{4}(\d{2})\d{2}/);
        if (m) {
            const yy = parseInt(m[1], 10);
            yearStr = String(yy >= 40 ? 1900 + yy : 2000 + yy);
        }
    }
    if (!yearStr) {
        const m2 = baseExp.match(/[A-Za-z]{4}(\d{2})\d{2}/);
        if (m2) {
            const yy = parseInt(m2[1], 10);
            yearStr = String(yy >= 40 ? 1900 + yy : 2000 + yy);
        }
    }

    const prettyPrimary = smartCase(chosen);
    const prettySecondary = smartCase(secondary);

    let label = [prettyPrimary, prettySecondary].filter(Boolean).join(' – ').trim();
    if (yearStr && !/\d{2,4}/.test(label)) {
        label = `${label} ${yearStr}`.trim();
    }

    return `${label} (${num})`;
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