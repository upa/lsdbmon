/* lsdbmon.js 
 * require jquery and d3js
 */

function lsdbmon_insert() {

	$.getJSON("lsadump.json", function(data) {

			insert_timestamp(data.timestamp);
			insert_adjacency(data.neighbor_info);
			//insert_graph(data["graph_info"]);
		});
}

function insert_timestamp(timestamp) {
	$('.timestamp').text(timestamp);
}

function insert_adjacency(neighbor_info) {

	for(var rtr_id in neighbor_info) {

		var content = '<tr>'
			+ '<td class="adj-box-source">'
			+ rtr_id + '</td><td>';

		for (var x in neighbor_info[rtr_id]) {
			var nei = neighbor_info[rtr_id][x];
			if (nei["type"] == "network") {
				content += '<div class="adj-box adj-box-net">';
			} else if (nei["type"] == "p2p") {
				content += '<div class="adj-box adj-box-p2p">';
			} else {
				content += '<div class="adj-box">';
			}
			content += nei["neighbor"] + '</div>';
		}
		content += '</td></tr>';
		$('table#adj-table tbody').append(content);
	}
}


lsdbmon_insert();