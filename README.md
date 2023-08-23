# PMD Demonstrator: processing remotely hosted data 

## The scientist's view: what do we practically do?
In this Notebook, we show exemplary how *ontologically described experimental data* (tensile tests on various S355 steel specimen) may be explored and processed. The database is hosted on a remote server running ontodocker. First, a manual exploration via SPARQL-queries is shown. We follow a set of questions, "translate" them into SPARQL-queries and discuss the obtained ouput. Then, data is processed using a pyiron-workflow. After analising a single dataset, we batch-process all available datasets while avoiding the formulation of explicit SPARQL-queries by the user. Mechanical quantities are calculated ($E$-modulus, $R_{p0.2}$) and stress-strain curves are plotted.

### Provided by the user:
- A material-digital account
- A SPARQL endpoint
- An user specific API-token (generated by keycloak and retievable via the ontodocker GUI).
  For running this notebook, this token has to be copied to a file `token.txt` located in the working directory.

## The infrasturcture view
"Under the hood" this procedure can be performed for a set of scenarios:
1. **All involved computers/servers are exposed to the internet**  
    The user works on an arbitrary computer which is connected to the internet.      
    The ontological database + infrastructure (triplestore = ontodocker) is hosted on the PMD-C ([ontodocker-dev.material-digital.de](ontodocker-dev.material-digital.de)) or any PMD-S which is exposed to the internet.
    Of course, the files containing the actual data also have to be either publicly available or available within the users subnet in this situation.

2. **All involved computers are exposed within the wireguard mesh**
   In this situation, the user is working on some PMD-S instance (e.g. [pyiron.material-digital.de](pyiron.material-digital.de)). There you can either select an appropriate image (e.g. "PMD Demonstrator") or some other pre-configured conda-environment within a jupyter session. Perhaps one has to install some more packages (e.g. for running this notebook, see `environment.yml`). The datafiles may be hosted either on some server available within the mesh or on the public internet.

3. **The user works on some machine within a strongly restricted environment** (e.g. @ BAM)
   Ontodocker and the datafiles are hosted on a server within the same network, the wireguard mesh or the internet.

From the user side, all these scenarios "feel the same", i.e. the interface and steps to perform do not differ (or may only differ to a trivial extend).
