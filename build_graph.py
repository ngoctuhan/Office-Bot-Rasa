import sys

from config import *


def print_log(text):
    sys.stdout.write(text)
    sys.stdout.flush()


def convert_edges_to_stories_with_checkpoint(infile):
    def remove_space_start(text):
        while text.startswith(" "):
            text = text[1:]
        return text

    edges_file = open(infile, "r")
    edges_set = set()
    ke = {}
    for line in edges_file.readlines():
        if line.startswith(">"):
            line = remove_space_start(line).split(">")
            action_pre = remove_space_start(line[1].strip())
            intent = remove_space_start(line[2].strip())
            action_next = remove_space_start(line[3].strip())
            if action_pre not in ke:
                ke[action_pre] = []
            ke[action_pre].append((intent, action_next))
    for action_pre in ke:
        for intent, action_next in ke[action_pre]:
            edges_set.add((action_pre, action_next, intent))
    edges_file.close()
    return edges_set


def build_graph_from_edges(edges_set, unmerge_nodes=None):
    if unmerge_nodes is None:
        unmerge_nodes = []
    nodes_set = set()
    parents = set()
    graph_list = []
    for u, v, intent in edges_set:
        nodes_set.add(u)
        nodes_set.add(v)
        parents.add(u)

    for u in nodes_set:
        if u not in parents:
            edges_set.add((u, "END", "None"))
    nodes_set.add("END")

    for u, v, intent in edges_set:
        node = {
            'pre_node': u,
            'cur_node': v,
            'intent': '/' + intent,
            'count': 0,
        }
        graph_list.append(node)
    edges = list(edges_set)
    nodes = list(nodes_set)

    mp_edges = set()
    list_intents = []
    list_actions = []
    fo = open(os.path.join(DIR_OUTPUT, "domain.txt"), "w")
    fo.write("intents:\n")
    for u, v, intent in edges_set:
        if intent != "None" and intent not in mp_edges:
            mp_edges.add(intent)
            list_intents.append(intent)
    list_intents.sort()
    for intent in list_intents:
        fo.write(f"- {intent}\n")
    fo.write("\n")
    fo.write("actions:\n")
    for node in nodes:
        if node != "START" and node != "END":
            list_actions.append(node)
    list_actions.sort()
    for action in list_actions:
        fo.write(f"- {action}\n")
    fo.close()

    import networkx as nx
    G = nx.MultiDiGraph()
    # G.add_nodes_from(nodes)
    unmerge_node_count_dict = dict()
    for unmerge_node in unmerge_nodes:
        unmerge_node_count_dict[unmerge_node] = 0
    # edge_labels = dict()
    # for node in graph_list:
    #    key = (node['pre_node'], node['cur_node'])
    #    if key not in edge_labels:
    #        edge_labeas[key] = []
    #    edge_labels[key].append(node['intent'])
    traveled_path = dict()
    for u, v, intent in edges:
        path = (u, intent)
        if path in traveled_path and traveled_path[path] != v:
            print_log("\n[ERROR] Found 2 conflict path:\n")
            print_log("[ERROR] Path1: {} ---{}--> {}\n".format(u, intent, v))
            print_log("[ERROR] Path1: {} ---{}--> {}\n".format(u, intent, traveled_path[path]))
            exit(1)
        traveled_path[path] = v
        if v in unmerge_node_count_dict:
            unmerge_node_count_dict[v] += 1
            v = "{}[{}]".format(v, unmerge_node_count_dict[v])
        G.add_nodes_from([u, v])
        G.add_edge(u, v, **{"label": intent})
    # expg = nx.nx_pydot.to_pydot(G)
    # print ("graph_list: ", graph_list)
    return graph_list, edges, nodes, G


if __name__ == "__main__":
    import pickle
    import argparse
    import os
    from rasa.core.training.visualization import persist_graph

    parser = argparse.ArgumentParser()
    parser.add_argument("infile", type=str, help="Input stories with edges")
    parser.add_argument("--config-graph", type=str, help="Output pickle graph config file",
                        default=PATH_CONFIG_GRAPH)
    parser.add_argument("--output-html", type=str, help="Output html graph", default=PATH_OUTPUT_GRAPH_HTML)
    parser.add_argument("--unmerge-nodes", type=str, help="Unmerge action node in graph, separate by comma",
                        default='action_sorry')

    args = parser.parse_args()
    assert os.path.exists(args.infile), "story-infile-edges {} not found!".format(args.infile)

    print_log("Reading edges from {} - \n".format(args.infile))
    edges_init = convert_edges_to_stories_with_checkpoint(args.infile)

    print_log("Building graph edges - ")
    graph_list, edges, nodes, graphviz = build_graph_from_edges(edges_init,
                                                                unmerge_nodes=args.unmerge_nodes.split(','))
    print_log("{} edges - {} nodes\n".format(len(edges), len(nodes)))

    pickle.dump(graph_list, open(args.config_graph, "wb"))
    print_log("Dump graph pickle in {}\n".format(args.config_graph))

    persist_graph(graphviz, args.output_html)
    print_log("Print graph to {}\n".format(args.output_html))