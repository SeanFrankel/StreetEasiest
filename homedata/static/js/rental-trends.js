// Configuration
const CHART_CONFIG = {
    colors: [
        'rgba(75, 192, 192, 1)',
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(0, 128, 0, 1)',
        'rgba(128, 0, 128, 1)'
    ],
    defaultSelections: {
        dataType: 'median',
        bedroom: 'All',
        neighborhood: 'Manhattan'
    }
};

class ChartManager {
    constructor() {
        this.chart = null;
        this.initializeControls();
        this.addEventListeners();
        this.updateChart();
    }

    initializeControls() {
        // Set default selections
        Object.entries(CHART_CONFIG.defaultSelections).forEach(([type, value]) => {
            const element = document.querySelector(`input[value="${value}"]`);
            if (element) element.checked = true;
        });
        
        document.getElementById('rawDataCheckbox').checked = true;
        document.getElementById('seasonalCheckbox').checked = false;
        document.getElementById('showBothCheckbox').checked = false;
    }

    addEventListeners() {
        // Add listeners for all control changes
        const controls = ['dataTypeContainer', 'bedroomContainer', 'checkboxContainer'];
        controls.forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.updateChart());
        });

        // Add listeners for seasonality controls
        ['rawDataCheckbox', 'seasonalCheckbox', 'showBothCheckbox', 'toggleInventorySecondary'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', (e) => {
                this.handleSeasonalityChange(e);
                this.updateChart();
            });
        });
    }

    handleSeasonalityChange(event) {
        const controls = {
            raw: document.getElementById('rawDataCheckbox'),
            seasonal: document.getElementById('seasonalCheckbox'),
            both: document.getElementById('showBothCheckbox')
        };

        if (event.target.checked) {
            Object.entries(controls).forEach(([key, control]) => {
                if (control !== event.target) control.checked = false;
            });
        }
    }

    getSelectedValues(containerId) {
        return Array.from(
            document.querySelectorAll(`#${containerId} input:checked`)
        ).map(cb => cb.value);
    }

    async updateChart() {
        const loadingIndicator = document.getElementById('loadingIndicator');
        loadingIndicator.classList.remove('hidden');

        try {
            const data = await this.fetchData();
            this.renderChart(data);
        } catch (error) {
            console.error('Error updating chart:', error);
            alert('Error updating chart. Please try again.');
        } finally {
            loadingIndicator.classList.add('hidden');
        }
    }

    async fetchData() {
        const selectedTypes = this.getSelectedValues('dataTypeContainer');
        const selectedBedrooms = this.getSelectedValues('bedroomContainer');
        const selectedNeighborhoods = this.getSelectedValues('checkboxContainer');

        const showSeasonalOnly = document.getElementById('seasonalCheckbox').checked;
        const showBoth = document.getElementById('showBothCheckbox').checked;
        const useSeasonalData = showSeasonalOnly || showBoth;

        const requests = [];
        selectedTypes.forEach(dt => {
            selectedBedrooms.forEach(bed => {
                selectedNeighborhoods.forEach(nb => {
                    const url = `/homedata/rental-data-json/?data=${dt}&bedrooms=${bed}&area=${nb}&seasonal=${useSeasonalData}`;
                    requests.push(fetch(url).then(response => response.json()));
                });
            });
        });

        return Promise.all(requests);
    }

    renderChart(responses) {
        const datasets = this.processDatasets(responses);
        if (datasets.length === 0) return;

        const ctx = document.getElementById('rentChart').getContext('2d');
        if (this.chart) this.chart.destroy();

        this.chart = new Chart(ctx, this.getChartConfig(datasets));
    }

    processDatasets(responses) {
        const datasets = [];
        const useSecondaryAxis = document.getElementById('toggleInventorySecondary').checked;
        const showSeasonalOnly = document.getElementById('seasonalCheckbox').checked;
        const showBoth = document.getElementById('showBothCheckbox').checked;

        responses.forEach(response => {
            Object.entries(response).forEach(([area, areaData]) => {
                if (!areaData.monthly) return;

                const isInventory = response.dataType === 'inventory';
                this.addDatasetForType(datasets, areaData, area, isInventory, useSecondaryAxis, showSeasonalOnly, showBoth);
            });
        });

        return datasets;
    }

    addDatasetForType(datasets, areaData, area, isInventory, useSecondaryAxis, showSeasonalOnly, showBoth) {
        const monthlyData = areaData.monthly;
        const yAxisID = useSecondaryAxis && isInventory ? 'y1' : 'y';

        if (!showSeasonalOnly && monthlyData.raw) {
            this.addDatasetToArray(datasets, {
                label: `${area} (${areaData.Borough}) - Raw ${isInventory ? 'Inventory' : 'Rent'}`,
                data: this.getDataPoints(monthlyData.raw),
                yAxisID
            });
        }

        if ((showSeasonalOnly || showBoth) && monthlyData.adjusted) {
            this.addDatasetToArray(datasets, {
                label: `${area} (${areaData.Borough}) - Seasonally Adjusted ${isInventory ? 'Inventory' : 'Rent'}`,
                data: this.getDataPoints(monthlyData.adjusted),
                yAxisID
            });
        }
    }

    getDataPoints(data) {
        const dates = Object.keys(data).sort();
        return dates.map(date => data[date]);
    }

    addDatasetToArray(datasets, dataset) {
        const color = CHART_CONFIG.colors[datasets.length % CHART_CONFIG.colors.length];
        datasets.push({
            ...dataset,
            borderColor: color,
            backgroundColor: color,
            fill: false
        });
    }

    getChartConfig(datasets) {
        const useSecondaryAxis = document.getElementById('toggleInventorySecondary').checked;
        const hasInventoryData = datasets.some(ds => ds.label.includes('Inventory'));

        return {
            type: 'line',
            data: {
                labels: this.getLabels(datasets[0].data),
                datasets
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
                    }
                },
                scales: this.getScalesConfig(useSecondaryAxis, hasInventoryData)
            }
        };
    }

    getLabels(data) {
        return Array.from({ length: data.length }, (_, i) => i + 1);
    }

    getScalesConfig(useSecondaryAxis, hasInventoryData) {
        const scales = {
            y: {
                type: 'linear',
                display: true,
                position: 'left',
                title: {
                    display: true,
                    text: 'Rent (USD)'
                }
            }
        };

        if (useSecondaryAxis && hasInventoryData) {
            scales.y1 = {
                type: 'linear',
                display: true,
                position: 'right',
                grid: {
                    drawOnChartArea: false
                },
                title: {
                    display: true,
                    text: 'Inventory Count'
                }
            };
        }

        return scales;
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => new ChartManager());