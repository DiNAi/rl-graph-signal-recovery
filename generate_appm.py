""" Generate an Assortative Planted Partition Model and a clustered graph
signal over the model. See S. Basirian, A. Jung "Random Walk Sampling for Big
Data over Networks" for details.
"""
import pathlib
import argparse

import networkx as nx
import numpy as np

from utils import dump_graph
from visualization import draw_partitioned_graph

def parse_args():
  parser = argparse.ArgumentParser(
    description="Creates an Assortative Planted Partition Model")

  parser.add_argument("--sizes",
                      type=int,
                      default=[10,20,30,40],
                      nargs='*',
                      help="Sizes of the groups to generate")

  parser.add_argument("--p_in",
                      type=float,
                      default=0.3,
                      help="Probability of connecting vertices within a group")

  parser.add_argument("--p_out",
                      type=float,
                      default=0.05,
                      help="Probability of connecting vertices between groups")

  parser.add_argument("--seed",
                      type=int,
                      default=None,
                      help="Random seed")

  parser.add_argument("--visualize",
                      action="store_true",
                      default=False,
                      help="Plot the generated graph")

  parser.add_argument("--out_path",
                      default=None,
                      help="Save graph output to out_path")

  parser.add_argument("--cull_disconnected",
                      action="store_true",
                      dest="cull_disconnected",
                      help="Cull nodes that are not connected to the main"
                           " graph")

  parser.add_argument("--no_cull_disconnected",
                      action="store_false",
                      dest="cull_disconnected",
                      help="Use to leave nodes that are not connected to the"
                           " main graph")

  parser.set_defaults(cull_disconnected=True)

  args = vars(parser.parse_args())
  return args

def add_signal_to_graph(graph):
  number_of_partitions = len(graph.graph["partition"])
  cluster_values = np.random.uniform(0,1,[number_of_partitions])
  for cluster_value, partition in zip(
      cluster_values, graph.graph["partition"]):
    for node_index in partition:
      graph.node[node_index]['value'] = cluster_value

def cull_disconnected_nodes(graph):
  connected_components = [c for c in sorted(nx.connected_components(graph),
                                            key=len,
                                            reverse=True)]
  for component in connected_components[1:]:
    graph.remove_nodes_from(component)

def main(args):
  sizes, p_in, p_out, seed = (args["sizes"], args["p_in"], args["p_out"],
                              args["seed"])
  visualize, out_path, cull_disconnected = (
      args["visualize"], args["out_path"], args['cull_disconnected'])

  np.random.seed(seed)

  appm = nx.random_partition_graph(sizes, p_in, p_out, seed=seed)
  add_signal_to_graph(appm)

  if cull_disconnected:
    cull_disconnected_nodes(appm)

  if visualize:
    draw_partitioned_graph(appm)

  appm = nx.convert_node_labels_to_integers(appm)

  if out_path is not None:
    if out_path.strip(".").strip("/").split("/")[0] == "data":
      pathlib.Path('./data').mkdir(parents=True, exist_ok=True)
    dump_graph(appm, out_path)
  else:
    return appm

if __name__ == "__main__":
  args = parse_args()
  main(args)
