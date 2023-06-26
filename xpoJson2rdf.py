#!/usr/bin/env python
# coding: utf-8

# XPO JSON to RDF
#  * Converts the JSON representation of the XPO knowledge graph to RDF
#    * The version of the XPO JSON file is from this [GitHub repository](https://github.com/e-spaulding/xpo)
#    * a 2023 paper describing it is [here](https://github.com/Ebiquity/xpo_rdf/blob/main/ISA2023_DWD_Overlay_Workshop_Paper.pdf)
#  * The resulting RDF graph uses two name space prefixes defined in purl that redirect to the xpo.nt file in the repository on GitHub
#    * xpo: http://purl.org/xpo/
#    * dwd: http://purl.org/dwd/
#  * We tried using a simpler approach that would make minor changes to the JSON file to make it JSON-LD and then using a standard tool to covert it to an RDF representation, but the format of the original xpo JSON file required to many structural changes.
# 
#  * we might want to extend this to add an addional schema statements to allow more inferences to be drawn


from rdflib import Graph, URIRef, Namespace, BNode, Literal
from rdflib.namespace import RDF, OWL, RDFS
import shortuuid 
import json

def bnode(prefix = ''):
    # custom BNode-like function adds a prefix to a short uuid sequence
    if prefix:
        return BNode(prefix + '_' + shortuuid.uuid()[:5])
    else:
        return BNode(shortuuid.uuid()[:5])


# Create and inital RDF graph and bind some namespace prefixes in it

GRAPH = Graph()

# unsure if we should use xpo or dwd as the profix
XPO = Namespace('http://purl.org/xpo/')
DWD = Namespace('http://purl.org/dwd/')

# use this namespace for the ontology
ONT = XPO

WD = Namespace('http://www.wikidata.org/wiki/')
WDP = Namespace('http://www.wikidata.org/wiki/Property:')

GRAPH.bind("dwd", DWD)
GRAPH.bind("xpo", XPO)

GRAPH.bind("owl", OWL)
GRAPH.bind("rdf", RDF)
GRAPH.bind('rdfs', RDFS)
GRAPH.bind('wd', WD)


# Get the XPO JSON file and extract the four subsets of data
#  * each is a dictionary where the keys are node ids and the values are dictionaries of their properties and values.
#  * for some prperaties the value is a list -- for these with generate multiple edges, one for each value in the list.
#  * we start by extracing the four top-level categories: events, entities, relations, and temopral_relations

xpo_data = json.load(open('xpo.json'))
event = xpo_data['events']
entity = xpo_data['entities']
relation = xpo_data['relations']
temporal_relation = xpo_data['temporal_relations']

# This is a list of all of the properties found in version 5.4.7

# these were extracted from the json file
all_properties = ['arguments', 'comment', 'constraints', 'curated_by', 
                  'dwd_arg_name', 'entities', 'events', 'ldc_argument_output_value', 
                  'ldc_arguments', 'ldc_code', 'ldc_constraints', 'ldc_name', 'ldc_types', 
                  'mapping_types', 'name', 'other_pb_rolesets', 'overlay_parents', 
                  'pb_mapping', 'pb_roleset', 'related_qnodes', 'relations', 'short_name', 
                  'similar_nodes', 'similarity_type', 'template', 'template_curation', 
                  'temporal_relations', 'type', 'version', 'wd_description', 'wd_node', 
                  'wd_slot']

def convert_generic(data, DWD=XPO, type="?", stop=0):
    count = 0 # just used for testing
    for (node, edges) in data.items():
        count += 1
        if stop > 0 and count > stop:
            break
        node = URIRef(DWD+node)
        for (property, value) in edges.items():
            if property in ['type', 'comment', 'curated_by', 'description', 
                              'wd_node', 'name', 'wd_description', 'template', 
                              'template_curation', 'pb_roleset']:
                # properties with a string value
                GRAPH.add((node, URIRef(DWD + property), Literal(value)))
            elif property == "overlay_parents":
                if isinstance(value, list):
                    for v in value:
                        overlay_node = bnode('OVERLAY')
                        GRAPH.add((node, DWD.overlay, overlay_node)) 
                        #GRAPH.add((overlay_node, RDF.type, DWD.overlay)) #overlay?
                        GRAPH.add((overlay_node, DWD.overlay_parent, URIRef(WD+v['wd_node'])))
                        GRAPH.add((overlay_node, DWD.overlay_parent_name, Literal(v['name'])))
                else:
                    print(f"Bad property-values {property} {value}")
            elif property == 'similar_nodes':
                if isinstance(value, list):
                    for v in value:
                        similar_node = bnode('SIMILAR')
                        GRAPH.add((node, DWD.similarNode, similar_node)) 
                        # GRAPH.add((similar_node, RDF.type, DWD.similar_node))
                        GRAPH.add((similar_node, DWD.wd_node, URIRef(WD+v['wd_node'])))
                        GRAPH.add((similar_node, DWD.name, Literal(v['name'])))
                        GRAPH.add((similar_node, DWD.similarity_type, URIRef(DWD+v['similarity_type'])))
                else:
                    print(f"Bad property-values {property} {value}")
            elif property == 'ldc_types':
                if isinstance(value, list):
                    # should be a list of dicts
                    for v in value:
                        ldc_type_node = bnode('LDCTYPE')
                        GRAPH.add((node, DWD.ldc_type, ldc_type_node))
                        for (vname, vvalue) in v.items():
                            if vname == 'name':
                                GRAPH.add((ldc_type_node, DWD.name, Literal(vvalue)))
                            elif vname == 'ldc_code':
                                GRAPH.add((ldc_type_node, DWD.ldc_code, Literal(vvalue)))
                            elif vname == 'other_pb_rolesets':
                                for pb_roleset in vvalue:
                                    GRAPH.add((ldc_type_node, DWD.other_pb_roleset, Literal(pb_roleset)))
                            elif vname == 'ldc_arguments':
                                for ldc_arg in vvalue:
                                    ldc_arg_node = bnode('LDCARG')
                                    GRAPH.add((ldc_type_node, DWD.ldc_argument, ldc_arg_node))
                                    for (ldc_arg_name, ldc_arg_value) in ldc_arg.items():
                                        if ldc_arg_name in ["ldc_name", "ldc_argument_output_value","dwd_arg_name"]:
                                            # all have simple string values
                                            GRAPH.add((ldc_arg_node, DWD.ldc_code, Literal(ldc_arg_value)))
                                    if ldc_arg_name == "ldc_contraints":
                                        for ent_type in ldc_arg_value:
                                            graph.add((ldc_arg_node, DWD.ldc_constraint, Literal(ent_type)))
                            else:
                                print(f"Bad LDC_types property (unrecognized): {node} {property} {vname}")
                else:
                    print(f"Bad property-values {property} {value} (not a list)")
            elif property == "arguments":
                if isinstance(value, list):
                    for arg in value:
                        # an arg should have a name, short_name and constraints
                        arg_node = bnode('ARG')
                        GRAPH.add((node, DWD.argument, arg_node))
                        if 'name' in arg: GRAPH.add((arg_node, DWD.name, Literal(arg['name'])))
                        if 'short_name' in arg: GRAPH.add((arg_node, DWD.short_name, Literal(arg['short_name'])))
                        for arg_constraint in arg['constraints']:
                            const_node = bnode('CONSTRAINT')
                            GRAPH.add((arg_node, DWD.constraint, const_node))
                            GRAPH.add((const_node, DWD.name, Literal(arg_constraint['name'])))
                            GRAPH.add((const_node, DWD.wd_node, URIRef(WD + arg_constraint['wd_node'])))
                else:
                    print(f"Bad property-values {node} {property} {value} (not a list)")
            elif property == "related_qnodes":
                if isinstance(value, list):
                    for v in value:
                        wdnode = bnode('WDNODE')
                        GRAPH.add((node, DWD.related_qnode, wdnode))
                        GRAPH.add((wdnode, DWD.wd_node, URIRef(WD+v['wd_node'])))
                        GRAPH.add((wdnode, DWD.name, Literal(v['name'])))
                else:
                    #raise exception, should be a list
                    print(f"Bad property-values {node} {property} {value}")
            # not recognized properties...
            else:
                if isinstance(value, list):
                    print(f"Unrecognized property with list of values for type {type}: {property} {value}")
                    if value == []:
                        #no values for this property, so ignore
                        pass
                    for v in value:
                        GRAPH.add((node, URIRef(DWD + property), Literal(v)))
                else:
                    print(f"Unrecognized property for {type}: {property} {value}")
                    GRAPH.add((node, URIRef(DWD + property), Literal(value))) 
    return count-1

N = 0 # set to a small number for testing

for (xpo_type, data) in [('event', event),
                         ('entity', entity),
                         ('relation', relation),
                         ('temporal_relation', temporal_relation)]: 
    n = convert_generic(data, type=xpo_type, stop=N)
    print(f"Found {n} {xpo_type}")

# ### Output RDF graph to xpo.ttl and xpo.nt

GRAPH.serialize(destination="xpo.ttl", format='turtle')
GRAPH.serialize(destination="xpo.nt", format='nt')





