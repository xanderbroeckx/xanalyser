#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 21:42:58 2024

@author: xanderbroeckx
"""

import tabula
import numpy as np
import pandas as pd
import os
from pprint import pprint;
#%%
# name pdf file
filepath = '/Users/xanderbroeckx/Documents/Annual Accounts Project/AA_VOL_Kap.pdf'
# get all the required tables 
#tables = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True)
#%%
def extract_financials(filepath):
    # Read all tables at once from the PDF file
    return tabula.read_pdf(filepath, pages='all', multiple_tables=True)

tables = extract_financials(filepath)
#%%
def create_mar(tables):
    # Concatenate account numbers data into a single DataFrame using a list comprehension
    
    
    return mar


mar = create_mar(tables)
#%%
account_numbers_full = pd.concat([tables[i] for i in range(6, len(tables))], axis=0)
#%%
account_numbers = account_numbers_full.Codes
account_numbers = account_numbers.fillna(value=account_numbers_full['Unnamed: 1'])
account_numbers = account_numbers.fillna(value = account_numbers_full['Codes Boekjaar'].str.split(' ',expand = True)[0])

#to get the value 
#CFY = CFY.fillna(value = account_numbers_full['Codes Boekjaar'].split(' ')[1])
#CFY = CFY.fillna(value = account_numbers_full['Codes Boekjaar']str..split(' ',expand = True)[1])
#%%
account_numbers.astype(str).str.replace(".0", "", regex=False)