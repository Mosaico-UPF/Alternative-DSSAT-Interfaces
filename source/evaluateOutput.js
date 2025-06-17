const OUTPUT_FILE_EXT = '.OUT';
const START_HEADER_DELIMITER = '@';
const BLANK_SPACE_DELIMITER = " ";
const EMPTY_DELIMITER = "";

class EvaluateOutput {
    constructor(fs, globalBasePath, cdeInstance) {
        this._fs = fs;
        this._globalBasePath = globalBasePath;
        this._cdeInstance = cdeInstance;
    }

    notEmptyString(value) {
        for (let i = 0; i < value.length; i++) {
            if (value[i] !== " " && value[i]) return true;
        }
        return false;
    }

    getOutFiles(crop) {
        let path = this._globalBasePath + crop;
        let cropFolderContent = this._fs.readdirSync(path);
        let outFiles = [];
        try {
            for (let i = 0; i < cropFolderContent.length; i++) {
                if (cropFolderContent[i].endsWith(OUTPUT_FILE_EXT) && cropFolderContent[i].toLowerCase().includes('evaluate')) {
                    outFiles.push(cropFolderContent[i]);
                }
            }
        } catch (error) {
            console.error('Error reading directory:', error);
        }
        return outFiles;
    }

    read(crop, outFile) {
        let path = this._globalBasePath + crop + "/" + outFile;
        let data;
        try {
            data = this._fs.readFileSync(path, 'utf8');
        } catch (error) {
            console.error(`Error reading file ${path}:`, error);
            return { results: [], timeField: null };
        }

        let lines = data.toString().split(/[\r\n]+/g).filter(line => line.trim() !== '');
        
        let headers = [];
        let results = [];
        const cdeData = this._cdeInstance.load();
        const timeHeaders = ['DATE', 'DAP', '@YEAR', 'DOY', 'TRNO'];
        let timeField = null;

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();

            if (line.startsWith('*')) continue;

            if (line.startsWith(START_HEADER_DELIMITER)) {
                const allHeaders = line.split(BLANK_SPACE_DELIMITER)
                    .filter(h => h !== EMPTY_DELIMITER && this.notEmptyString(h))
                    .map(h => h.trim());

                headers = allHeaders.filter(header => 
                    header.endsWith('M') || header.endsWith('S') || timeHeaders.includes(header.toUpperCase())
                );

                headers.indices = allHeaders
                    .map((h, idx) => ({ header: h, index: idx }))
                    .filter(h => headers.includes(h.header))
                    .map(h => h.index);

                timeField = headers.find(h => timeHeaders.includes(h.toUpperCase())) || 'TRNO';
                console.log('Detected headers:', headers, 'Time field:', timeField);
                continue;
            }

            if (this.notEmptyString(line) && headers.length > 0) {
                let values = line.split(BLANK_SPACE_DELIMITER)
                    .filter(v => v !== EMPTY_DELIMITER && this.notEmptyString(v))
                    .map(v => v.trim());

                if (values.length >= headers.indices[headers.indices.length - 1] + 1) {
                    let record = {};
                    // Group headers by base name
                    let headerGroups = {};
                    headers.forEach((header, index) => {
                        const baseHeader = header.replace(/(S|M)$/, ''); // Remove S or M suffix
                        if (!headerGroups[baseHeader]) {
                            headerGroups[baseHeader] = {};
                        }
                        const valueIndex = headers.indices[index];
                        const rawValue = values[valueIndex];
                        let value = rawValue;
                        if (!timeHeaders.includes(header.toUpperCase())) {
                            value = isNaN(rawValue) || rawValue === '-99' ? null : parseFloat(rawValue);
                        }
                        const type = header.endsWith('M') ? 'measured' : header.endsWith('S') ? 'simulated' : 'time';
                        headerGroups[baseHeader][header] = {
                            value: value,
                            cde: header,
                            type: type
                        };
                        console.log(`Processing header: ${header}, base: ${baseHeader}, value: ${value}`);
                    });

                    // Create a single record per base header
                    for (let baseHeader in headerGroups) {
                        const group = headerGroups[baseHeader];
                        let simulated = null, measured = null;
                        if (group[baseHeader + 'S']) simulated = group[baseHeader + 'S'].value;
                        if (group[baseHeader + 'M']) measured = group[baseHeader + 'M'].value;
                        // Use simulated as fallback if measured is null
                        if (measured === null && simulated !== null) measured = simulated;
                        record[baseHeader] = {
                            simulated: simulated,
                            measured: measured,
                            cde: baseHeader,
                            description: group[baseHeader + 'S'] ? group[baseHeader + 'S'].description : (group[baseHeader + 'M'] ? group[baseHeader + 'M'].description : baseHeader),
                            type: 'combined'
                        };
                        console.log(`Merged record for ${baseHeader}: simulated=${simulated}, measured=${measured}`);
                    }

                    // Add time field if present
                    if (timeField && headers.includes(timeField)) {
                        const timeIndex = headers.indices[headers.indexOf(timeField)];
                        record[timeField] = {
                            value: values[timeIndex],
                            cde: timeField,
                            type: 'time'
                        };
                    }

                    results.push(record);
                }
            }
        }

        return { results, timeField };
    }
}

module.exports = EvaluateOutput;