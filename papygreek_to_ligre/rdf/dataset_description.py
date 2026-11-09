from collections import Counter

from rdflib import BNode, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, XSD

from .. import settings
from .namespaces import DC, LILA, LILA_CORPUS, POWLA

VOID = Namespace("http://rdfs.org/ns/void#")
TURTLE_FORMAT = URIRef("http://www.w3.org/ns/formats/Turtle")
TURTLE_MEDIA_TYPE = URIRef("https://www.iana.org/assignments/media-types/text/turtle")
DCAT_VERSION = URIRef(str(DCAT) + "version")
GZIP_MEDIA_TYPE = URIRef("https://www.iana.org/assignments/media-types/application/gzip")
ANCIENT_GREEK = URIRef("http://lexvo.org/id/iso639-3/grc")
VOCABULARIES = (POWLA, LILA, LILA_CORPUS, DC, DCTERMS)


def bind_description_prefixes(graph):
    for prefix, namespace in (("void", VOID), ("dcat", DCAT), ("foaf", FOAF)):
        graph.bind(prefix, namespace, override=True)


class DatasetStatistics:

    def __init__(self):
        self.triples = 0
        self.entities = 0
        self.instances = Counter()
        self.properties = Counter()
        self.lemma_links = 0
        self.linked_lemmas = set()
        self.first_document = None

    def add(self, graph, subjects):
        for subject in subjects:
            counted = False
            for predicate, value in graph.predicate_objects(subject):
                counted = True
                self.triples += 1
                self.properties[predicate] += 1
                if predicate == RDF.type:
                    self.instances[value] += 1
                    if value == POWLA.Document and self.first_document is None:
                        self.first_document = subject
                elif predicate == LILA.hasLemma:
                    self.lemma_links += 1
                    self.linked_lemmas.add(value)
            self.entities += counted


def add_agent(graph, dataset, predicate, agent):
    node = URIRef(agent["iri"]) if agent.get("iri") else BNode()
    graph.add((dataset, predicate, node))
    graph.add((node, RDF.type, FOAF.Agent))
    graph.add((node, FOAF.name, Literal(agent["name"])))
    return node if isinstance(node, URIRef) else None


def knowledge_base_iri(lemma_bank):
    return URIRef(str(lemma_bank).split("/data/id/lemma/")[0] + "/data/id/KnowledgeBase")


def describe_corpus(graph, corpus, lemma_bank, statistics):
    agents = []
    graph.add((corpus, RDF.type, VOID.Dataset))
    graph.add((corpus, RDF.type, DCAT.Dataset))

    graph.add((corpus, DCTERMS.title, Literal(settings.CORPUS_TITLE, lang="en")))
    graph.add((corpus, DCTERMS.description, Literal(settings.CORPUS_DESCRIPTION, lang="en")))
    for creator in settings.CORPUS_CREATORS:
        agents.append(add_agent(graph, corpus, DCTERMS.creator, creator))
    if settings.CORPUS_PUBLISHER:
        agents.append(add_agent(graph, corpus, DCTERMS.publisher, settings.CORPUS_PUBLISHER))
    graph.add((corpus, DCTERMS.language, ANCIENT_GREEK))
    license_document = URIRef(settings.PAPYGREEK_LICENSE_URL)
    graph.add((license_document, RDF.type, DCTERMS.LicenseDocument))
    graph.add((license_document, DCTERMS.title,
               Literal("Creative Commons Attribution Share Alike 4.0 International", lang="en")))
    graph.add((corpus, DCTERMS.source, URIRef(settings.PAPYGREEK_DOI)))
    graph.add((corpus, DCTERMS.isPartOf, knowledge_base_iri(lemma_bank)))
    if settings.CORPUS_DOI:
        graph.add((corpus, DCTERMS.identifier, Literal(settings.CORPUS_DOI)))
    graph.add((corpus, DCAT_VERSION, Literal(settings.CORPUS_VERSION)))
    if settings.CORPUS_ISSUED:
        graph.add((corpus, DCTERMS.issued, Literal(settings.CORPUS_ISSUED, datatype=XSD.date)))
    if settings.CORPUS_BIBLIOGRAPHIC_CITATION:
        graph.add((corpus, DCTERMS.bibliographicCitation, Literal(settings.CORPUS_BIBLIOGRAPHIC_CITATION)))
    graph.add((corpus, DCTERMS.conformsTo, URIRef(str(LILA_CORPUS).rstrip("/"))))

    for keyword in settings.CORPUS_KEYWORDS:
        graph.add((corpus, DCAT.keyword, Literal(keyword, lang="en")))
    graph.add((corpus, DCAT.landingPage, URIRef(settings.CORPUS_REPOSITORY_URL)))
    graph.add((corpus, FOAF.homepage, URIRef(settings.KNOWLEDGE_BASE_HOMEPAGE)))
    download = URIRef(settings.CORPUS_DOWNLOAD_URL)
    distribution = BNode()
    graph.add((corpus, DCAT.distribution, distribution))
    graph.add((distribution, RDF.type, DCAT.Distribution))
    graph.add((distribution, DCTERMS.title, Literal("Complete corpus in Turtle (gzip)", lang="en")))
    graph.add((distribution, DCAT.downloadURL, download))
    graph.add((distribution, DCAT.mediaType, TURTLE_MEDIA_TYPE))
    graph.add((distribution, DCAT.compressFormat, GZIP_MEDIA_TYPE))
    graph.add((distribution, DCTERMS.license, license_document))
    if settings.CORPUS_DOI:
        graph.add((distribution, DCTERMS.identifier, Literal(settings.CORPUS_DOI)))
    graph.add((distribution, DCAT.accessURL, URIRef(settings.CORPUS_DOI or settings.CORPUS_RELEASE_URL)))
    if settings.CORPUS_ISSUED:
        graph.add((distribution, DCTERMS.issued, Literal(settings.CORPUS_ISSUED, datatype=XSD.date)))

    graph.add((corpus, VOID.dataDump, download))
    graph.add((corpus, VOID.feature, TURTLE_FORMAT))
    graph.add((corpus, VOID.uriSpace, Literal(f"{corpus}/")))
    if statistics.first_document is not None:
        graph.add((corpus, VOID.exampleResource, statistics.first_document))
    for vocabulary in VOCABULARIES:
        graph.add((corpus, VOID.vocabulary, URIRef(str(vocabulary))))
    graph.add((corpus, VOID.triples, Literal(statistics.triples, datatype=XSD.integer)))
    graph.add((corpus, VOID.entities, Literal(statistics.entities, datatype=XSD.integer)))
    graph.add((corpus, VOID.classes, Literal(len(statistics.instances), datatype=XSD.integer)))
    graph.add((corpus, VOID.properties, Literal(len(statistics.properties), datatype=XSD.integer)))
    for rdf_class, count in sorted(statistics.instances.items()):
        partition = BNode()
        graph.add((corpus, VOID.classPartition, partition))
        graph.add((partition, VOID["class"], rdf_class))
        graph.add((partition, VOID.entities, Literal(count, datatype=XSD.integer)))
    for rdf_property, count in sorted(statistics.properties.items()):
        partition = BNode()
        graph.add((corpus, VOID.propertyPartition, partition))
        graph.add((partition, VOID.property, rdf_property))
        graph.add((partition, VOID.triples, Literal(count, datatype=XSD.integer)))

    linkset = BNode()
    graph.add((corpus, VOID.subset, linkset))
    graph.add((linkset, RDF.type, VOID.Linkset))
    graph.add((linkset, DCTERMS.title, Literal("PapyGreek tokens linked to LiGre lemmas", lang="en")))
    graph.add((linkset, VOID.subjectsTarget, corpus))
    graph.add((linkset, VOID.objectsTarget, lemma_bank))
    graph.add((linkset, VOID.linkPredicate, LILA.hasLemma))
    graph.add((linkset, VOID.triples, Literal(statistics.lemma_links, datatype=XSD.integer)))
    graph.add((linkset, VOID.distinctObjects, Literal(len(statistics.linked_lemmas), datatype=XSD.integer)))
    return [agent for agent in agents if agent is not None] + [license_document]
