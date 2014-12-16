
# coding: utf-8

# In[37]:

import re
import pprint
import glob

records = []
current_record = None
previous_record = ''

for f in glob.glob('rivdocset*.txt'):
    with open(f,'r') as docset:
        for line in docset.readlines():
            # This checks whether the line includes a record type 
            # (i.e. two capital letters at the start of the line)
            m = re.match(r'^(\w{2})\s(.+)\n$',line)

            # If there's a match, we'll initialise the record type.
            if m:
                record_type = m.group(1)
                record_value = m.group(2)

                # 'PT' signifies the start of a new record
                if record_type == 'PT' and current_record != None:
                    records.append(current_record)
                    current_record = {}
                    current_record[record_type] = [record_value]
                # 'EF' signifies the end of file
                elif record_type == 'EF':
                    records.append(current_record)
                # If we already have a record dictionary (current_record) append the record value 
                # to the list of values for the current record type
                elif current_record != None :
                    current_record.setdefault(record_type,[]).append(record_value)
                # Otherwise, we initialize a new record dictionary
                else :
                    current_record = {record_type: [record_value]}

                # Keep track of the previous record
                previous_record = record_value
                # Continue to the next line
                continue

            # Otherwise, the line clearly does not start with a record type
            m = re.match(r'^\s+(.+)\n$',line)
            # We match the value listed on the line, and append the value to the most recent
            # record type in the current record dictionary.
            if m:
                record_value = m.group(1)
                current_record[record_type].append(record_value)
                # Keep track of the previous record
                previous_record = record_value
        
      





        


# In[38]:

def fix_records(records):
    new_records = []
    for record in records:
        record = concatenate_record(record)
        record = parse_citations(record)
        record = build_id(record)
        new_records.append(record)
        
    return new_records

def concatenate_record(record):
    """This appends lines for some records (e.g. the abstract)"""
    new_record = {}
    for k,v in record.items():
        if k in ['AB','FX','PA','TI','RP','ID']:
            new_v = ' '.join(v)
            
            if k == 'ID':
                new_v = new_v.split('; ')
            
            new_record[k] = new_v
        elif k == 'CR':
            previous_citation = ''
            new_citations = []
            for citation in v:
                if previous_citation.endswith('DOI'):
                    new_citations[-1] += ' ' + citation
                    previous_citation = new_citations[-1]
                else :
                    new_citations.append(citation)
                    previous_citation = citation
                    
            new_record[k] = new_citations
        else :
            new_record[k] = v
    
    return new_record
        
 
def parse_citations(record):
    
    if 'CR' in record.keys():
        citations = record['CR']
        
        new_citations = []
        
        
        for citation in citations:
            citation_list = citation.split(', ')
            citation_dict = {}
            
            id_list = [c.replace(' ','_') for c in citation_list if not(c.startswith('ARTN ') or c.startswith('DOI '))]
            
            for c in citation_list:
                if c.startswith('DOI '):
                    citation_dict['doi'] = urllib.quote(c[4:])
            
            citation_dict['qname'] = ''.join(id_list)
            citation_dict['citation'] = citation_list
            
            
            
            new_citations.append(citation_dict)
            
        
        
        
        record['CR'] = new_citations
                
    return record

def build_id(record):
    try :
        if 'AU' in record.keys():
            author = record['AU'][0].replace(', ',' ').replace(' ','_').upper()
        else : 
            author = ''
            
        if 'PY' in record.keys():
            year = record['PY'][0]
        else :
            year = ''
        
        if 'J9' in record.keys():
            journal = record['J9'][0].replace(' ','_')
        else:
            journal = ''
            
        if 'VL' in record.keys():
            volume = 'V' + record['VL'][0]
        else:
            volume = ''

        if 'DI' in record.keys():
            doi = record['DI'][0]

        if 'BP' in record.keys():
            page = 'P' + record['BP'][0]
        else :
            page = ''


        record['qname'] = '{}{}{}{}{}'.format(author,year,journal,volume,page)
        
        return record
    except Exception as e:
        print e
        pprint.pprint(record)
        
        raise e
    


fixed_records = fix_records(records)


# In[39]:

from rdflib import Graph, URIRef, Literal, Namespace, RDF, OWL, RDFS, BNode
import urllib

RV = Namespace('http://data.data2semantics.org/vocab/')
R = Namespace('http://data.data2semantics.org/resource/')
DOI = Namespace('http://dx.doi.org/')

g = Graph()

g.bind('r', R)
g.bind('rv', RV)
g.bind('doi',DOI)
g.bind('owl',OWL)

resources = ['GA','ID','J9','JI','PI','SC','SN','SO','LA','PT','PY','UT','DT','EM','CR','DI','AU']

count = 0

# Are authors considered unique per article, or will we smush authors with literally the same name
UNIQUE_AUTHORS = True

for r in fixed_records:
    count += 1
    uri = R[r['qname']]
    
    if 'DT' in r.keys():
        g.add((uri,RDF.type,RV[r['DT'][0].replace(' ','_')]))
    
    for k,v in r.items():
        if k in resources:
            for val in v: 
                ## Citations
                if isinstance(val, dict) and k == 'CR':
                    citation_uri = R[val['qname']]
                    g.add((uri, RV[k], citation_uri))
                    g.add((citation_uri, RDFS.label, Literal(' '.join(val['citation']))))
                    
                    if 'doi' in val.keys():
                        g.add((citation_uri, OWL['sameAs'], DOI[val['doi']]))
                    
                    for i in val['citation']:
                        urival = R[urllib.quote(i.replace(' ','_'))]
                        g.add((urival, RDFS.label, Literal(i)))
                        g.add((citation_uri,RV['part'],urival))
                ## Authors
                elif k == 'AU':
                    if UNIQUE_AUTHORS :
                        urival = R[r['qname'] + '/' + val.replace(', ',' ').replace(' ','_')]
                        
                    else :
                        urival = R[val.replace(', ',' ').replace(' ','_')]
                    g.add((urival,RDFS.label,Literal(val)))
                    g.add((uri,RV[k],urival))
                ## Everything else
                else :
                    urival = R[val.replace(' ','_')]
                    g.add((urival,RDFS.label,Literal(val)))
                    g.add((uri,RV[k],urival))
        else :
            if isinstance(v, list): 
                for val in v:
                    g.add((uri,RV[k],Literal(val)))
            else:
                g.add((uri,RV[k],Literal(v)))
            
            
    


# In[40]:

out = open('rivers.nt','w')
g.serialize(out,format='nt')
out.close()


# In[ ]:



