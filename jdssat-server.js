const express = require('express')
const jdssat = require('./jdssat')
const app = express()
const port = 3000
const simVsObs = require('./source/simVsObs');

app.get('/', (request, response) => response.send('server is up and running'))

app.listen(port, function() {
    console.log(`app listening on port ${port}!`)
})

app.use(function (request, response, next) {
    response.header("Access-Control-Allow-Origin", "*");
    response.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
})

app.get('/api/treatments/:crop/:experiments', (request, response) => {
    let crop = request.params.crop;
    let experiments = request.params.experiments;
    let experimentsObj = JSON.parse(experiments);
    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    let treatments = jdssatInstance.treatments(crop, experimentsObj);
    response.end(JSON.stringify(treatments));
})

app.get('/api/experiments/:crop', (request, response) => {
    let crop = request.params.crop;
    console.log(crop);
    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    let experiments = jdssatInstance.experiments(crop);
    response.end(JSON.stringify(experiments));
})

app.get('/api/data/:crop', (request, response) => {
    let crop = request.params.crop;
    console.log(crop);
    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    let experiments = jdssatInstance.getDataFiles(crop);
    response.end(JSON.stringify(experiments));
})

app.get('/api/outfiles/:crop', (request, response) => {
    let crop = request.params.crop;
    console.log(crop);
    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    let outFiles = jdssatInstance.outFiles(crop);

    response.end(JSON.stringify(outFiles));
})

app.get('/api/runSimulation/:crop/:experiments', (request, response) => {
    let crop = request.params.crop;
    let experiments = request.params.experiments;
    let experimentsObj = JSON.parse(experiments);

    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    jdssatInstance.runSimulation(crop, experimentsObj);

    response.end("simulations are completed");
})

app.get('/api/out/:crop/:file', (request, response) => {
    let crop = request.params.crop;
    let outfile = request.params.file;

    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    let fileContent = jdssatInstance.readOutFile(crop, outfile);

    response.end(JSON.stringify(fileContent));
})

app.get('/api/t/:crop/:file', async (request, response) => {
    let crop = request.params.crop;
    let tfile = request.params.file;

    jdssatInstance = new jdssat();
    jdssatInstance.initialize();

    let fileContent = await jdssatInstance.readTFile(crop, tfile);
    
    // Transform T-file data to match OUT file structure
    const transformedData = fileContent.map(entry => {
        // Convert single values to arrays like OUT files
        const values = entry.values.map(v => ({
            cde: v.cde,
            values: Array.isArray(v.values) ? v.values : [v.values]
        }));
        
        return {
            run: entry.runName || entry.run,
            experiment: entry.experiment,
            day: entry.day || 0, // Use provided day or default
            values: values
        };
    });

    response.json(transformedData);
});

app.get('/api/cde', (request, response) => {

    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    let cdeVariables = jdssatInstance.cde();

    response.end(JSON.stringify(cdeVariables));
})

app.get('/api/tool/', (request, response) => {

    //let tool = request.params.tool;
    let tool = request.query.tool;

    console.log(tool);

    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    jdssatInstance.openExternalTool(tool);

    response.end(JSON.stringify("ok"));
})

app.get('/api/config/', (request, response) => {
    let config = request.query.config;

    console.log(config);

    jdssatInstance = new jdssat();
    jdssatInstance.initialize();

    if (config === "path") {
        let path = jdssatInstance.path();
        response.end(JSON.stringify(path));
    } else if (config === "version") {
        let version = jdssatInstance.version();
        response.end(JSON.stringify(version));
    } else if (config === "platform") {
        let platform = jdssatInstance.platform();
        response.end(JSON.stringify(platform));
    } else{
    response.end(JSON.stringify("not found"));
    }
})
app.get('/api/evaluate/:crop/:file', (request, response) => {
    let crop = request.params.crop;
    let file = request.params.file;
    jdssatInstance = new jdssat();
    jdssatInstance.initialize();
    try {
        let fileContent = jdssatInstance.readEvaluateFile(crop, file);
        response.json(fileContent);
    } catch (error) {
        console.error('Error reading evaluate file:', error);
        response.status(500).json({ error: 'Error reading evaluate file' });
    }
});
app.get('/api/sim-vs-obs/:crop/:outfile', async (req, res) => {
  const crop = req.params.crop;                
  const outFile = req.params.outfile;          
  try {
    const result = await simVsObs.loadSimVsObsFromOutFile(crop, outFile);
    res.json(result);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to load Simulated vs Observed data.' });
  }
});

