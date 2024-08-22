# LogPPL: A Tool for Probabilistic Process Mining
LogPPL is a powerful tool that bridges the gap between Data Petri Nets (DPNs) and probabilistic programming, allowing for the generation of event logs with statistical guarantees. By transforming DPNs into probabilistic programs using WebPPL. LogPPL offers a robust framework for simulating complex process behaviors under uncertainty.
This tool builds on the approach introduced in:
* 	*Martin Kuhn, Joscha Grüger, Christoph Matheja, Andrey Rivkin*: Data Petri Nets meet Probabilistic Programming (Extended version). CoRR abs/2406.11883 (2024)

## Key Features
- **Statistical Modeling**: Provides a statistically grounded approach to simulating process behaviors.
- **Simplified Configuration**: Easily configure probabilistic parameters, including queries and schedulers.
- **Export Options**: Supports exporting event logs in XES format and WebPPL files for further analysis.


## Installation using Docker

Detailed installation instructions are found further below.
For simplicity, we also provide a `Dockerfile` that takes care of all installation steps.
After installing and starting [Docker](https://www.docker.com/get-started/), it suffices to run the following from command line (in the directory of our artifact):

1. Build the docker container: `docker build -t icpm_demo .`
2. Run the container in interactive mode: `docker run -p 5000:5000 icpm_demo`
3. One can now run the tool in the browser by following the local host link provided in the terminal.
```
python examples/example_create_webppl.py
```
The result webppl file is then found in `examples/webppl_files/simple_auction.wppl`:
```
cat examples/webppl_files/simple_auction.wppl
```

Similarly, to produce an XES event log for our running example, it suffices to run the following script in the docker container:
```
python examples/example_create_event_log.py
```
The resulting XES file can be accessed as follows:
```
cat examples/xes_files/simple_auction.xes
```

To exit the docker container, it suffices to run `exit`.

## Installation without Docker
To use the DPN to WebPPL Converter, ensure that you have Python 3.x installed on your system. Follow these steps to set up the converter:

1. Download and install Node.js (which includes npm) from the official Node.js website (https://nodejs.org/en). Choose the LTS (Long Term Support) version for the most stable and supported setup. After installation, you can verify that Node.js and npm are correctly installed by running the following commands in your command line:
```bash
node -v
npm -v
```

2. Once Node.js and npm are installed, you can install WebPPL globally using npm. You can install WebPPL by following the instructions. 
```bash
npm install -g webppl
```

3. Clone the repository to your local machine using the following command or by downloading the repository as a zip file and extracting it to a local directory:
```bash
git clone <repository-anonymized>
```

4. Navigate to the root directory of the repository: 
```bash
cd <repository-name>
```

5. Install the required dependencies using the following command:
```bash
pip install -r requirements.txt
```



## Contributing
* **Martin Kuhn**, German Research Center for Artificial Intelligence (DFKI), SDS Branch Trier, Trier, Germany
* **Joscha Grüger**, University of Trier & German Research Center for Artificial Intelligence (DFKI), SDS Branch Trier, Trier, Germany
* **Christoph Matheja**, Technical University of Denmark, Kgs. Lyngby, Denmark
* **Andrey Rivkin**, Technical University of Denmark, Kgs. Lyngby, Denmark

