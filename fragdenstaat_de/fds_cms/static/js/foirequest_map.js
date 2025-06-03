
// Cache for status icons
const statusIconCache = {};

function getStatusIcon(status) {
    if (statusIconCache[status]) {
        return statusIconCache[status];
    }

    const statusColors = {
        'awaiting_response': 'bg-secondary',
        'successful': 'bg-success',
        'partially_successful': 'bg-success',
        'refused': 'bg-danger',
        'overdue': 'bg-warning',
    };

    const statusClass = statusColors[status] || 'bg-secondary';
    const icon = L.divIcon({
        className: 'foirequest-map-custom-icon',
        html: `<div class="${statusClass}"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });

    statusIconCache[status] = icon;
    return icon;
}

function htmlEscape(str) {
    return str.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&#39;');
}

function createPopupContent(requests) {
    let popupHtml = '<div class="foirequest-map-popup">';
    requests.forEach((request, index) => {
        popupHtml += `
            <h4 class="fs-5"><a href="${request.url}">${htmlEscape(request.title)}</a></h4>
            <p class="mt-0">${htmlEscape(request.public_body_name)}</p>
            <p class="text-body-secondary">${htmlEscape(request.status_display)}</p>
            ${index < requests.length - 1 ? '<hr>' : ''}
        `;
    });
    popupHtml += '</div>';
    return popupHtml;
}

function getColorMode() {
  return document.documentElement.getAttribute('data-bs-theme') || 'light'
}


function initMap(mapId) {
    const mapData = JSON.parse(document.getElementById(`foirequest_map_plugin_data_${mapId}`).textContent);

    // Initialize map with zoom controls
    const map = L.map(`foirequest_map_plugin_${mapId}`, {
        zoomControl: true,
        scrollWheelZoom: true
    }).setView([51.1657, 10.4515], 6);
    map.attributionControl.setPrefix('')

    // Add OpenStreetMap tiles
    const tileLayerUrl = `//cartodb-basemaps-{s}.global.ssl.fastly.net/${getColorMode()}_all/{z}/{x}/{y}${window.L.Browser.retina ? '@2x' : ''}.png`

    L.tileLayer(tileLayerUrl, {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attribution">CARTO</a>'
    }).addTo(map);

    function onEachFeature(feature, layer) {
        if (feature.properties && feature.properties.requests) {
            layer.bindPopup(createPopupContent(feature.properties.requests));
        }
    }

    const geoLayer = L.geoJSON(mapData.geojson, {
        // style: function (feature) {},
        pointToLayer: function (feature, latlng) {
            // return L.circleMarker(latlng, geojsonMarkerOptions);
            return L.marker(latlng, {
                icon: getStatusIcon(feature.properties.requests[0].status)
            })
        },
        onEachFeature: onEachFeature
    })
    geoLayer.addTo(map);
    map.fitBounds(geoLayer.getBounds());
    
    // Add legend
    var legend = L.control({position: 'bottomright'});
    legend.onAdd = function (map) {
        const template = document.getElementById(`foirequest_map_plugin_template_${mapId}`)
        return template.content.cloneNode(true).children[0]
    };
    legend.addTo(map);
}


document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-foirequest-cms-map').forEach(function (element) {
        const mapId = element.dataset.foirequestCmsMap
        if (mapId) {
            initMap(mapId)
        }
    })
})
