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

    def query_raw_data_url(self, dataset):
        sparql = SPARQLWrapper(self.endpoint)
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)
        sparql.setReturnFormat("json")
        
        sparql.addCustomHttpHeader(httpHeaderName="Authorization", httpHeaderValue=self.access_token)

        # to access the actual raw data
        def do_replacements(urls, orign_strings=["github.com", "tree/"], replacements=["raw.githubusercontent.com", ""]):
            for orign_str, repl in zip(orign_strings, replacements):
                urls = [new.replace(orign_str, repl) for new in urls]
            return(urls)
            
        sparql.setQuery(
            """
            PREFIX pmd: <https://w3id.org/pmd/co/>
            SELECT distinct ?raw
            WHERE {{
            ?table <http://www.w3.org/ns/csvw#url> ?raw .
            FILTER (str(?raw)='https://github.com/materialdigital/application-ontologies/tree/main/tensile_test_ontology_TTO/data/primary_data/{dat:s}.csv')
            }} ORDER BY ?table
            """.format(dat=dataset))
        
        list=[]
        try:
            ret = sparql.queryAndConvert()
            for r in ret["results"]["bindings"]:
                row = []
                for k in r.keys():
                    row.append(r[k]['value'])
                list.append(row)

        except Exception as e:
            print(e)
            
        self.raw_data_url=do_replacements([list[0][0]])[0]

    def query_crossSectionalArea(self, dataset):
        self.input.crosssection = 0.000000115

    def query_column(self, quantity):
        # returns column number containing resp. quantity
        pass

    def query_strain_column():
        # returns column number containing strain/percentageElongation in %*100.
        pass
        
    def load_force_strain_from_url(self):
        data = pd.read_csv(self.raw_data_url, delimiter=";", decimal=",", on_bad_lines='skip', skiprows=[1])

        def convert_number(num):
            num = num.replace(',', '.')
            return float(num)

        self.input.force = data['Load'].to_numpy()

        def convert_strain(strain):
            return (strain-strain[0])/100.
            
        self.input.strain = convert_strain(data['Extensometer elongation'].to_numpy())

    def calc_stress(self):
        self.input.stress = self.input.force/self.input.crosssection

    def calc_elastic_modulus(self, elastic_strain_lim=0.001):
        def lin_func(x,a,b):
            return a*x+b

        elastic_lim_index = 0
        while self.input.strain[elastic_lim_index] <= elastic_strain_lim:
            elastic_lim_index += 1

        popt, pcov = curve_fit(lin_func, self.input.strain[:elastic_lim_index], self.input.stress[:elastic_lim_index])

        self.output.elastic_modulus = popt[0]
        self.output.stress_offset = popt[1]
        self.output.variance_elastic_modulus = pcov[0,0]
        self.output.variance_stress_offset = pcov[1,1]

    def calc_Rp02(self):
        linear_line = self.output.elastic_modulus*((self.input.strain[:800])-0.02)
        diff = self.input.strain[:800]-linear_line
        arg = np.argmin(diff)
        self.output.Rp02 = self.input.stress[arg]

    def run_static(self):
        self.calc_elastic_modulus()
        self.calc_Rp02()
        self.to_hdf()
        self.status.finished = True