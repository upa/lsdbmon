/* lsdbmon.js 
 * require jquery and d3js
 */

function lsdbmon_insert() {

	$.getJSON("lsadump.json", function(data) {

			insert_timestamp(data.timestamp);
			insert_adjacency(data.neighbor_info);
			insert_graph(data["graph_info"]);
		});
}

function insert_timestamp(timestamp) {
	$('.timestamp').text(timestamp);
}

function insert_adjacency(neighbor_info) {

	for (var i = 0; i < neighbor_info.length; i++) {

		rtr = neighbor_info[i];

		var content = '<tr>'
			+ '<td class="adj-box-source">'
			+ rtr.router_id + '</td><td>';

		for (var x = 0; x < rtr.neighbors.length; x++) {
			var nei = rtr.neighbors[x];
			if (nei.type == "network") {
				content += '<div class="adj-box adj-box-net">';
			} else if (nei.type == "p2p") {
				content += '<div class="adj-box adj-box-p2p">';
			} else {
				content += '<div class="adj-box">';
			}
			content += nei.router_id + '</div>';
		}
		content += '</td></tr>';
		$('table#adj-table tbody').append(content);
	}
}




function insert_graph(graph) {
	var svg = d3.select("svg"),
		width = +svg.attr("width"),
		height = +svg.attr("height");

	var color = d3.scaleOrdinal(d3.schemeCategory20);

	var simulation = d3.forceSimulation()
		.force("link", d3.forceLink().id(function(d) { return d.id; }))
		.force("charge", d3.forceManyBody())
		.force("center", d3.forceCenter(width / 2, height / 2));

	var link = svg.append("g")
		.attr("class", "links")
		.selectAll("line")
		.data(graph.links)
		.enter().append("line")
		.attr("stroke-width", function(d) { return 2; });

	var node = svg.append("g")
		.attr("class", "nodes")
		.selectAll("circle")
		.data(graph.nodes)
		.enter().append("circle")
		.attr("r", function(d) {
				if (d.type == "network") {
					return 4.5;
				} else if (d.type == "router") {
					return 7;
				} else {
					return color(1);
				}
			})
		.attr("fill", function(d) { 
				if (d.type == "network") {
					return "#3cb37a";
				} else if (d.type == "router") {
					return "#e95464";
				} else {
					return color(1);
				}
			})
		.call(d3.drag()
		      .on("start", dragstarted)
		      .on("drag", dragged)
		      .on("end", dragended));

	node.append("title")
		.text(function(d) { return d.name; });

	simulation
		.nodes(graph.nodes)
		.on("tick", ticked);

	simulation.force("link")
		.links(graph.links);

	function ticked() {
		link
			.attr("x1", function(d) { return d.source.x; })
			.attr("y1", function(d) { return d.source.y; })
			.attr("x2", function(d) { return d.target.x; })
			.attr("y2", function(d) { return d.target.y; });

		node
			.attr("cx", function(d) { return d.x; })
			.attr("cy", function(d) { return d.y; });
	}

	function dragstarted(d) {
		if (!d3.event.active) simulation.alphaTarget(0.3).restart();
		d.fx = d.x;
		d.fy = d.y;
	}

	function dragged(d) {
		d.fx = d3.event.x;
		d.fy = d3.event.y;
	}

	function dragended(d) {
		if (!d3.event.active) simulation.alphaTarget(0);
		d.fx = null;
		d.fy = null;
	}
}

lsdbmon_insert();