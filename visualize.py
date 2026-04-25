import json
import networkx as nx
import matplotlib.pyplot as plt

def generate_map_visualization(config_file="world_config.json", output_file="map_visualization.png"):
    with open(config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cities = data["map"]["cities"]
    edges = data["map"]["edges"]

    G = nx.Graph()
    for city in cities:
        G.add_node(city)
    
    for edge in edges:
        G.add_edge(edge["from"], edge["to"], weight=edge["days"])

    pos = nx.spring_layout(G, seed=42)
    
    plt.figure(figsize=(10, 8))
    
    # Draw network
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=2000, font_size=16, font_weight='bold', edge_color='gray')
    
    # Draw edge labels (days)
    edge_labels = {(edge["from"], edge["to"]): f'{edge["days"]}d' for edge in edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')

    # Draw optimal route overlay (A -> B -> C -> D -> E -> D) based on our engine's result
    route = ["A", "B", "C", "D", "E", "D"]
    route_edges = [(route[i], route[i+1]) for i in range(len(route)-1)]
    
    nx.draw_networkx_edges(G, pos, edgelist=route_edges, edge_color='blue', width=3, arrows=True, arrowstyle='->', arrowsize=20)

    plt.title("The Zoldyck Assassination Contract Board - Optimal Route Overlay", fontsize=16)
    plt.savefig(output_file)
    print(f"Map visualization saved to {output_file}")

if __name__ == "__main__":
    generate_map_visualization()
