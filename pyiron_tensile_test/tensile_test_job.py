from pyiron_base import PythonTemplateJob, DataContainer
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from scipy.optimize import curve_fit
import requests
from SPARQLWrapper import SPARQLWrapper, JSON
import os
import json


class TensileJob(PythonTemplateJob):
    def __init__(self, project, job_name):
        super(TensileJob, self).__init__(project, job_name)
        self._endpoint = None
        self._access_token = None
        self._process_uri = None
        self._raw_data_url = None
        self._set_local_path = False

    @property
    def endpoint(self):
        return self._endpoint

    @endpoint.setter
    def endpoint(self, url):
        self._endpoint = url

    @property
    def access_token(self):
        return self._access_token

    @access_token.setter
    def access_token(self, access_token):
        self._access_token = access_token

    @property
    def process_uri(self):
        return self._process_uri

    @process_uri.setter
    def process_uri(self, process_uri):
        self._process_uri = process_uri

    @property
    def raw_data_url(self):
        return self._raw_data_url

    @raw_data_url.setter
    def raw_data_url(self, url):
        self._raw_data_url = url

    @property
    def set_local_path(self):
        return self._set_local_path

    @set_local_path.setter
    def set_local_path(self, slp):
        self._set_local_path = slp
        
    def query_cross_section_area(self):
        sparql = SPARQLWrapper(self.endpoint)
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        sparql.setReturnFormat("json")
        
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        
        sparql.setQuery("""
        PREFIX pmd: <https://w3id.org/pmd/co/>
        SELECT distinct ?p ?S0val ?unit
        WHERE {{
        ?s a pmd:TestPiece .
        ?p a pmd:TensileTest .
        ?p pmd:input ?s .
        ?p pmd:characteristic ?output .
        ?output a pmd:CrossSectionArea .
        ?output pmd:value ?S0val .
        ?output pmd:unit ?unit .
        FILTER regex(str(?output), "S0")
        FILTER regex(str(?p), "{0:s}")
        }} ORDER BY ?p
        """.format(self.uri)
                        )

        res = sparql.queryAndConvert()
        cross_section = float(res["results"]["bindings"][0]["S0val"]["value"]) # cross_section in (mm)^2
        cross_section *= 1e-09 # convert to m^2
        self.input.cross_section = cross_section

    def query_raw_data_url(self):
        sparql = SPARQLWrapper(self.endpoint)
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        sparql.setReturnFormat("json")
        
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        
        sparql.setQuery("""
        PREFIX base: <https://w3id.org/pmd/co/>
        PREFIX csvw: <http://www.w3.org/ns/csvw#>
        SELECT ?url ?p
        WHERE {{
        ?p a base:TensileTest .
        ?p base:characteristic ?dataset .
        ?dataset a base:Dataset .
        ?dataset base:resource ?table .
        ?table a csvw:Table .
        ?table csvw:url ?url .
        FILTER regex(str(?p), "{0:s}")
        }}
        ORDER BY ?p
        """.format(self.uri)
                        )

        res = sparql.queryAndConvert()

        self.input.raw_data_url= res["results"]["bindings"][0]["url"]["value"]
            
        
    def query_column(self, quantity):
        sparql = SPARQLWrapper(self.endpoint)
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        sparql.setReturnFormat("json")
        
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        
        sparql.setQuery("""
        SELECT DISTINCT ?part (count(?mid) AS ?column_num) ?type ?unit
        WHERE {{
        ?table <http://www.w3.org/ns/csvw#url> ?url .
        ?table <http://www.w3.org/ns/csvw#tableSchema> ?schema .
        ?schema <http://www.w3.org/ns/csvw#column>/rdf:rest* ?mid .
        ?mid rdf:rest* ?node .
        ?node rdf:first ?part .
        ?part a ?type .
        ?part <https://w3id.org/pmd/co/unit> ?unit .
        FILTER (?type!=<http://www.w3.org/ns/csvw#Column>)
        FILTER (str(?url)='{0:s}')
        }}
        GROUP BY ?node ?part ?type ?url ?unit ORDER BY ?column_num
        """.format(self.input.raw_data_url)
                        )

        res = sparql.queryAndConvert()
        
        column_dict = {}
        for d in res['results']['bindings']:
            column_dict[d['type']['value']] = {
                'unit': d['unit']['value'],
                'column_number': d['column_num']['value']
            }
        return(column_dict[quantity]['column_number'])
        
    def load_force_and_strain(self):

        force_column_number = int(self.query_column('https://w3id.org/pmd/co/Force'))-1
        strain_column_number = int(self.query_column('https://w3id.org/pmd/co/PercentageExtension'))-1

        # correct the url to access the raw data, not the html site...
        def do_replacements(urls, orign_strings=["github.com", "tree/"], replacements=["raw.githubusercontent.com", ""]):
            for orign_str, repl in zip(orign_strings, replacements):
                urls = [new.replace(orign_str, repl) for new in urls]
            return(urls)
        
        self.input.raw_data_url= do_replacements([self.input.raw_data_url])[0]

        # set a local path, in case the data hosted online is corrupted
        def set_csv_path():
            ret = self.input.raw_data_url
        
            if self.set_local_path :
                ret = self.input.raw_data_url.replace('https://raw.githubusercontent.com/materialdigital/application-ontologies/main/tensile_test_ontology_TTO/data/primary_data/', '/home/bruns/dap/examples/S355_SteelSheet/input_data/01_primary_data/')

            return(ret)
        
        datapath = set_csv_path()
        data = pd.read_csv(datapath, delimiter=";", decimal=",", on_bad_lines='skip', skiprows=[1])

        def convert_strain(strain):
            return (strain-strain[0])/100.
            
        self.input.strain = convert_strain(data.iloc[:,strain_column_number].to_numpy())
        self.input.force = data.iloc[:,force_column_number].to_numpy()

    def calc_stress(self):
        self.input.stress = self.input.force/self.input.cross_section

    def calc_elastic_modulus(self, elastic_strain_lim=0.001):
        def lin_func(x,a,b):
            return a*x+b

        elastic_lim_index = 0
        while self.input.strain[elastic_lim_index] <= elastic_strain_lim:
            elastic_lim_index += 1

        popt, pcov = curve_fit(lin_func, self.input.strain[:elastic_lim_index+1], self.input.stress[:elastic_lim_index+1], p0=np.asarray([400000.,-1000000.]))

        self.output.elastic_modulus = popt[0]
        self.output.stress_offset = popt[1]
        self.output.variance_elastic_modulus = pcov[0,0]
        self.output.variance_stress_offset = pcov[1,1]
        self.output.elastic_strain_lim = self.input.strain[elastic_lim_index]
        self.output.elastic_lim_index = elastic_lim_index
        
    def calc_Rp02(self):
        linear_line = self.output.elastic_modulus*((self.input.strain[:900])-0.02)
        diff = self.input.strain[:900]-linear_line
        arg = np.argmin(diff)
        self.output.Rp02 = self.input.stress[arg]

    def run_static(self):
        self.query_cross_section_area()
        self.query_raw_data_url()
        self.load_force_and_strain()
        self.calc_stress()
        self.calc_elastic_modulus()
        self.calc_Rp02()
        self.to_hdf()
        self.status.finished = True
