// Define a color palette to keep colors consistent
const colorPalette = {
    'Manhattan': '#4e79a7',
    'Brooklyn': '#f28e2c',
    'Queens': '#e15759',
    'Bronx': '#76b7b2',
    'Staten Island': '#59a14f',
    'All': '#af7aa1',
    'median': '#4e79a7',
    'inventory': '#f28e2c',
    'Studio': '#e15759',
    'OneBd': '#76b7b2',
    'TwoBd': '#59a14f',
    'ThreePlusBd': '#af7aa1'
};

// Color cache to ensure consistent colors for the same data series
const colorCache = {};

// Helper function to convert hex to HSL
function hexToHSL(hex) {
    hex = hex.replace(/^#/, '');
    let r = parseInt(hex.substr(0, 2), 16) / 255;
    let g = parseInt(hex.substr(2, 2), 16) / 255;
    let b = parseInt(hex.substr(4, 2), 16) / 255;
    
    let max = Math.max(r, g, b);
    let min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;

    if (max === min) {
        h = s = 0;
    } else {
        let d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }

    return {
        h: Math.round(h * 360),
        s: Math.round(s * 100),
        l: Math.round(l * 100)
    };
}

// Helper function to convert HSL to hex
function hslToHex({ h, s, l }) {
    l /= 100;
    const a = s * Math.min(l, 1 - l) / 100;
    const f = n => {
        const k = (n + h / 30) % 12;
        const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
        return Math.round(255 * color).toString(16).padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
}

// Generate a deterministic color based on key parameters
function getConsistentColor(dataType, bedroom, neighborhood) {
    const key = `${dataType}_${bedroom}_${neighborhood}`;
    
    if (colorCache[key]) {
        return colorCache[key];
    }
    
    if (colorPalette[neighborhood]) {
        const baseColor = colorPalette[neighborhood];
        if (bedroom !== 'All') {
            const hslColor = hexToHSL(baseColor);
            if (dataType === 'inventory') {
                hslColor.l = Math.min(hslColor.l + 15, 90);
            }
            if (bedroom === 'Studio') hslColor.h = (hslColor.h + 10) % 360;
            if (bedroom === 'OneBd') hslColor.h = (hslColor.h + 20) % 360;
            if (bedroom === 'TwoBd') hslColor.h = (hslColor.h + 30) % 360;
            if (bedroom === 'ThreePlusBd') hslColor.h = (hslColor.h + 40) % 360;
            
            colorCache[key] = hslToHex(hslColor);
        } else {
            colorCache[key] = baseColor;
        }
    } else {
        let hash = 0;
        for (let i = 0; i < key.length; i++) {
            hash = key.charCodeAt(i) + ((hash << 5) - hash);
        }
        const h = Math.abs(hash) % 360;
        colorCache[key] = hslToHex({ h, s: 70, l: 60 });
    }
    
    return colorCache[key];
}

// Initialize everything when the DOM is loaded
document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM Content Loaded");
    
    // Add neighborhood search functionality
    document.getElementById('checkboxFilter').addEventListener('input', function() {
        const filterValue = this.value.toLowerCase();
        const container = document.getElementById('checkboxContainer');
        const checkboxDivs = container.getElementsByTagName('div');
        for (let i = 0; i < checkboxDivs.length; i++) {
            const labelText = checkboxDivs[i].querySelector('label').textContent.toLowerCase();
            checkboxDivs[i].style.display = (labelText.indexOf(filterValue) > -1) ? '' : 'none';
        }
    });

    // Set default selections
    function setDefaultSelections() {
        if (!document.querySelector("#dataTypeContainer input:checked")) {
            document.querySelector("#dataTypeContainer input[value='median']").checked = true;
        }
        if (!document.querySelector("#bedroomContainer input:checked")) {
            document.querySelector("#bedroomContainer input[value='All']").checked = true;
        }
        if (!document.querySelector("#checkboxContainer input:checked")) {
            document.querySelector("#checkboxContainer input[value='Manhattan']").checked = true;
        }
        document.getElementById('rawDataCheckbox').checked = true;
        document.getElementById('seasonalCheckbox').checked = false;
        document.getElementById('showBothCheckbox').checked = false;
    }

    // Add event listeners for data display options
    function addDataDisplayListeners() {
        document.getElementById('rawDataCheckbox').addEventListener('change', function() {
            if (this.checked) {
                document.getElementById('seasonalCheckbox').checked = false;
                document.getElementById('showBothCheckbox').checked = false;
            }
            updateChart();
        });

        document.getElementById('seasonalCheckbox').addEventListener('change', function() {
            if (this.checked) {
                document.getElementById('rawDataCheckbox').checked = false;
                document.getElementById('showBothCheckbox').checked = false;
            }
            updateChart();
        });

        document.getElementById('showBothCheckbox').addEventListener('change', function() {
            if (this.checked) {
                document.getElementById('rawDataCheckbox').checked = false;
                document.getElementById('seasonalCheckbox').checked = false;
            }
            updateChart();
        });
    }

    // Add event listeners for other controls
    function addControlListeners() {
        document.getElementById('checkboxContainer').addEventListener('change', updateChart);
        document.getElementById('dataTypeContainer').addEventListener('change', updateChart);
        document.getElementById('bedroomContainer').addEventListener('change', updateChart);
        document.getElementById('toggleInventorySecondary').addEventListener('change', updateChart);
    }

    // Reset filters function
    function resetFilters(e) {
        if (e) e.preventDefault();
        document.getElementById('dt_median').checked = true;
        document.getElementById('dt_inventory').checked = false;
        document.getElementById('bed_All').checked = true;
        document.getElementById('bed_Studio').checked = false;
        document.getElementById('bed_OneBd').checked = false;
        document.getElementById('bed_TwoBd').checked = false;
        document.getElementById('bed_ThreePlusBd').checked = false;
        const neighborhoodCheckboxes = document.querySelectorAll("#checkboxContainer input[type='checkbox']");
        neighborhoodCheckboxes.forEach(cb => { cb.checked = (cb.value === "Manhattan"); });
        document.getElementById('toggleInventorySecondary').checked = false;
        document.getElementById('checkboxFilter').value = "";
        document.getElementById('rawDataCheckbox').checked = true;
        document.getElementById('seasonalCheckbox').checked = false;
        document.getElementById('showBothCheckbox').checked = false;
        updateChart();
    }

    // Initialize everything
    setDefaultSelections();
    addDataDisplayListeners();
    addControlListeners();
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
    
    // Initial chart render
    console.log("Triggering initial chart update");
    updateChart();
});

// Update Chart function
function updateChart() {
    console.log("updateChart called");
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.classList.remove('hidden');

    // Get selected data types
    let dataTypeCheckboxes = document.querySelectorAll("#dataTypeContainer input[type='checkbox']:checked");
    let selectedDataTypes = Array.from(dataTypeCheckboxes).map(cb => cb.value);
    console.log("Selected data types:", selectedDataTypes);

    // Get selected bedroom types
    let bedroomCheckboxes = document.querySelectorAll("#bedroomContainer input[type='checkbox']:checked");
    let selectedBedroomTypes = Array.from(bedroomCheckboxes).map(cb => cb.value);
    console.log("Selected bedroom types:", selectedBedroomTypes);

    // Get selected neighborhoods
    let neighborhoodCheckboxes = document.querySelectorAll("#checkboxContainer input[type='checkbox']:checked");
    let selectedNeighborhoods = Array.from(neighborhoodCheckboxes).map(cb => cb.value);
    console.log("Selected neighborhoods:", selectedNeighborhoods);

    // Get seasonality state
    const rawDataCheckbox = document.getElementById('rawDataCheckbox');
    const seasonalCheckbox = document.getElementById('seasonalCheckbox');
    const showBothCheckbox = document.getElementById('showBothCheckbox');
    const showSeasonalOnly = seasonalCheckbox.checked;
    const showBoth = showBothCheckbox.checked;
    const useSeasonalData = showSeasonalOnly || showBoth;

    console.log("Seasonality state:", { showSeasonalOnly, showBoth, useSeasonalData });

    if (selectedDataTypes.length === 0 || selectedBedroomTypes.length === 0 || selectedNeighborhoods.length === 0) {
        console.log("No selections made in required fields");
        if (window.rentChartInstance) { window.rentChartInstance.clear(); }
        loadingIndicator.classList.add('hidden');
        return;
    }

    let requests = [];
    selectedDataTypes.forEach(dt => {
        selectedBedroomTypes.forEach(bed => {
            selectedNeighborhoods.forEach(nb => {
                const url = `/homedata/rental-data-json/?data=${dt}&bedrooms=${bed}&area=${encodeURIComponent(nb)}&seasonal=${useSeasonalData}`;
                console.log("Fetching URL:", url);
                requests.push(
                    fetch(url)
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`HTTP error! status: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(jsonData => {
                            if (jsonData.error) {
                                throw new Error(jsonData.error);
                            }
                            console.log("Received data for:", dt, bed, nb, jsonData);
                            return { dataType: dt, bedroom: bed, neighborhood: nb, jsonData: jsonData };
                        })
                        .catch(error => {
                            console.error("Error fetching data:", error);
                            loadingIndicator.classList.add('hidden');
                            return null;
                        })
                );
            });
        });
    });

    Promise.all(requests)
        .then(responses => {
            // Filter out failed requests
            responses = responses.filter(r => r !== null);
            
            console.log("All responses received:", responses);
            let datasets = [];
            let labels = null;
            const useSecondaryAxis = document.getElementById('toggleInventorySecondary').checked;

            responses.forEach(response => {
                if (!response.jsonData) return;
                
                Object.entries(response.jsonData).forEach(([area, areaData]) => {
                    if (!areaData || !areaData.monthly) {
                        console.warn(`Invalid data for ${area}`);
                        return;
                    }

                    const monthlyData = areaData.monthly;
                    const isInventory = response.dataType === 'inventory';

                    // Handle raw data
                    if (!showSeasonalOnly && monthlyData.raw) {
                        const dates = Object.keys(monthlyData.raw).sort();
                        const values = dates.map(date => monthlyData.raw[date]);
                        
                        const color = getConsistentColor(response.dataType, response.bedroom, area);
                        
                        datasets.push({
                            label: `${area} - ${response.bedroom} - Raw ${isInventory ? 'Inventory' : 'Rent'}`,
                            data: values,
                            borderColor: color,
                            backgroundColor: color,
                            fill: false,
                            spanGaps: false,
                            yAxisID: useSecondaryAxis && isInventory ? 'y1' : 'y'
                        });
                        if (!labels) labels = dates;
                    }

                    // Handle seasonal data
                    if ((showSeasonalOnly || showBoth) && monthlyData.adjusted) {
                        const dates = Object.keys(monthlyData.adjusted).sort();
                        const values = dates.map(date => monthlyData.adjusted[date]);
                        
                        let color = getConsistentColor(response.dataType, response.bedroom, area);
                        const hslColor = hexToHSL(color);
                        hslColor.l = Math.max(hslColor.l - 15, 30);
                        color = hslToHex(hslColor);
                        
                        datasets.push({
                            label: `${area} - ${response.bedroom} - Adjusted ${isInventory ? 'Inventory' : 'Rent'}`,
                            data: values,
                            borderColor: color,
                            backgroundColor: color,
                            fill: false,
                            yAxisID: useSecondaryAxis && isInventory ? 'y1' : 'y'
                        });
                        if (!labels) labels = dates;
                    }
                });
            });

            console.log("Created datasets:", datasets);
            
            // Create or update chart
            const ctx = document.getElementById('rentChart').getContext('2d');
            if (window.rentChartInstance) {
                // Update the labels
                window.rentChartInstance.data.labels = labels;

                // Update the datasets
                window.rentChartInstance.data.datasets = datasets;
                // redraw only new parts
                window.rentChartInstance.update('none');
            } else {

                if (datasets.length > 0 && labels) {
                    const hasInventoryData = datasets.some(ds => ds.label.includes('Inventory'));
                    
                    window.rentChartInstance = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false
                            },
                            plugins: {
                                tooltip: {
                                    mode: 'index',
                                    intersect: false
                                },
                                legend: {
                                    position: 'top'
                                },
                                title: {
                                    display: true,
                                    text: 'NYC Rental Trends',
                                    font: {
                                        size: 16,
                                        weight: 'bold'
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    beginAtZero: false,
                                    title: {
                                        display: true,
                                        text: 'Rent (USD)'
                                    }
                                },
                                ...(useSecondaryAxis && hasInventoryData ? {
                                    y1: {
                                        type: 'linear',
                                        display: true,
                                        position: 'right',
                                        beginAtZero: false,
                                        grid: {
                                            drawOnChartArea: false
                                        },
                                        title: {
                                            display: true,
                                            text: 'Inventory Count'
                                        }
                                    }
                                } : {})
                            }
                        }
                    });
                    console.log("Chart created successfully");
                } else {
                    console.warn("No valid datasets to display");
                }
            }

            loadingIndicator.classList.add('hidden');
        })
        .catch(error => {
            console.error("Error creating chart:", error);
            loadingIndicator.classList.add('hidden');
        });
} 

function downloadPDF() {
    // Get the canvas as an image
    const canvas = window.rentChartInstance.canvas;
    const image = canvas.toDataURL('image/png');

    // Create jsPDF instance
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Add the image to the PDF (positioning it on the page)
    doc.addImage(image, 'PNG', 10, 10, 180, 160); // Adjust position and size as needed

    // Save the PDF
    doc.save('chart.pdf');
}

function downloadExcel() {
    // Convert chart data to a format suitable for Excel
    const data = window.rentChartInstance.data;
    const labels = data.labels;
    const datasets = data.datasets;

    // Prepare the data for export
    const sheetData = [];
    sheetData.push(['Month', ...datasets.map(dataset => dataset.label)]); // Headers
    labels.forEach((label, index) => {
      const row = [label];
      datasets.forEach(dataset => {
        row.push(dataset.data[index]);
      });
      sheetData.push(row);
    });

    // Create a worksheet and workbook
    const ws = XLSX.utils.aoa_to_sheet(sheetData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Chart Data');

    // Export the data to an Excel file
    XLSX.writeFile(wb, 'chart_data.xlsx');
}