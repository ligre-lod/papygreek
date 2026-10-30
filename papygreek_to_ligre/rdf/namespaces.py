from rdflib import Graph, Namespace
from rdflib.namespace import DC, DCTERMS, RDF, RDFS, XSD

POWLA = Namespace("http://purl.org/powla/powla.owl#")
LILA = Namespace("http://lila-erc.eu/ontologies/lila/")
LILA_CORPUS = Namespace("http://lila-erc.eu/ontologies/lila_corpora/")
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")


def ligre_lemma_namespace(base_iri):
    return Namespace(f"{base_iri.rstrip('/')}/data/id/lemma/")


def create_graph(lemma_namespace):
    graph = Graph(bind_namespaces="none")
    prefixes = {
        "rdf": RDF,
        "rdfs": RDFS,
        "xsd": XSD,
        "dc": DC,
        "dcterms": DCTERMS,
        "powla": POWLA,
        "lilaOntology": LILA,
        "lila_corpus": LILA_CORPUS,
        "ligreLemma": lemma_namespace,
    }
    for prefix, namespace in prefixes.items():
        graph.bind(prefix, namespace, override=True)
    return graph
