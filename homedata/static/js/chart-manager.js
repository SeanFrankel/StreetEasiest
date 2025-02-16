import CHART_CONFIG from './chart-config.js';
import { DataFetcher, FetchError } from './data-fetcher.js';
import { DataTypes, BedroomTypes } from './data-types.js';

class ChartManager {
  constructor() {
    this.chart = null;
    this.loadingIndicator = document.getElementById('loadingIndicator');
    this.initializeControls();
    this.addEventListeners();
    this.updateChart(); // Initial chart render
  }

  initializeControls() {
    this.setDefaultSelections();
    this.setSeasonalityDefaults();
  }

  setDefaultSelections() {
    Object.entries(CHART_CONFIG.defaultSelections).forEach(([type, value]) => {
      const element = document.querySelector(`input[value="${value}"]`);
      if (element) element.checked = true;
    });
  }

  setSeasonalityDefaults() {
    const controls = {
      raw: document.getElementById('rawDataCheckbox'),
      seasonal: document.getElementById('seasonalCheckbox'),
      both: document.getElementById('showBothCheckbox')
    };

    if (controls.raw) controls.raw.checked = true;
    if (controls.seasonal) controls.seasonal.checked = false;
    if (controls.both) controls.both.checked = false;
  }

  addEventListeners() {
    ['dataTypeContainer', 'bedroomContainer', 'checkboxContainer'].forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        element.addEventListener('change', () => this.updateChart());
      }
    });

    ['rawDataCheckbox', 'seasonalCheckbox', 'showBothCheckbox', 'toggleInventorySecondary'].forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        element.addEventListener('change', (e) => {
          this.handleSeasonalityChange(e);
          this.updateChart();
        });
      }
    });
  }

  async updateChart() {
    if (this.loadingIndicator) {
      this.loadingIndicator.classList.remove('hidden');
    }

    try {
      const selections = {
        dataTypes: this.getSelectedValues('dataTypeContainer'),
        bedrooms: this.getSelectedValues('bedroomContainer'),
        neighborhoods: this.getSelectedValues('checkboxContainer'),
        useSeasonalData: document.getElementById('seasonalCheckbox')?.checked || 
                        document.getElementById('showBothCheckbox')?.checked || 
                        false
      };

      if (!this.validateSelections(selections)) {
        console.warn('No selections made');
        return;
      }

      const responses = await DataFetcher.fetchMultipleDatasets(selections);
      await this.renderChart(responses);
    } catch (error) {
      console.error('Error updating chart:', error);
    } finally {
      if (this.loadingIndicator) {
        this.loadingIndicator.classList.add('hidden');
      }
    }
  }

  getSelectedValues(containerId) {
    const container = document.getElementById(containerId);
    return container ? 
      Array.from(container.querySelectorAll('input:checked')).map(cb => cb.value) :
      [];
  }

  validateSelections(selections) {
    return selections.dataTypes.length > 0 && 
           selections.bedrooms.length > 0 && 
           selections.neighborhoods.length > 0;
  }

  async renderChart(responses) {
    const ctx = document.getElementById('rentChart')?.getContext('2d');
    if (!ctx) {
      console.error('Chart canvas not found');
      return;
    }

    const datasets = this.processDatasets(responses);
    if (datasets.length === 0) {
      console.warn('No data to display');
      return;
    }

    this.destroyChart();
    
    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: this.generateLabels(datasets[0].data.length),
        datasets: datasets
      },
      options: this.getChartOptions()
    });
  }

  processDatasets(responses) {
    const datasets = [];
    const useSecondaryAxis = document.getElementById('toggleInventorySecondary')?.checked || false;
    const showSeasonalOnly = document.getElementById('seasonalCheckbox')?.checked || false;
    const showBoth = document.getElementById('showBothCheckbox')?.checked || false;

    responses.forEach(response => {
      Object.entries(response.data).forEach(([areaName, areaData]) => {
        const isInventory = response.dataType === DataTypes.INVENTORY;
        const monthlyData = areaData.monthly;
        
        if (!monthlyData) {
          console.warn(`No monthly data for ${areaName}`);
          return;
        }

        if (!showSeasonalOnly && monthlyData.raw) {
          datasets.push({
            label: `${areaName} (${response.bedroom}) - ${isInventory ? 'Inventory' : 'Rent'}`,
            data: Object.values(monthlyData.raw),
            borderColor: CHART_CONFIG.colors[datasets.length % CHART_CONFIG.colors.length],
            backgroundColor: CHART_CONFIG.colors[datasets.length % CHART_CONFIG.colors.length],
            yAxisID: useSecondaryAxis && isInventory ? 'y1' : 'y',
            fill: false
          });
        }

        if ((showSeasonalOnly || showBoth) && monthlyData.adjusted) {
          datasets.push({
            label: `${areaName} (${response.bedroom}) - Adjusted ${isInventory ? 'Inventory' : 'Rent'}`,
            data: Object.values(monthlyData.adjusted),
            borderColor: CHART_CONFIG.colors[datasets.length % CHART_CONFIG.colors.length],
            backgroundColor: CHART_CONFIG.colors[datasets.length % CHART_CONFIG.colors.length],
            yAxisID: useSecondaryAxis && isInventory ? 'y1' : 'y',
            fill: false,
            borderDash: [5, 5]
          });
        }
      });
    });

    console.log('Generated datasets:', datasets);
    return datasets;
  }

  generateLabels(dataLength) {
    const startDate = new Date('2010-01');
    return Array.from({ length: dataLength }, (_, i) => {
      const date = new Date(startDate);
      date.setMonth(startDate.getMonth() + i);
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
    });
  }

  getChartOptions() {
    const useSecondaryAxis = document.getElementById('toggleInventorySecondary')?.checked || false;
    
    const options = {
      ...CHART_CONFIG.chartDefaults,
      scales: {
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: {
            display: true,
            text: 'Rent (USD)'
          }
        }
      }
    };

    if (useSecondaryAxis) {
      options.scales.y1 = {
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

    return options;
  }

  handleSeasonalityChange(event) {
    if (event.target.checked) {
      ['rawDataCheckbox', 'seasonalCheckbox', 'showBothCheckbox'].forEach(id => {
        const element = document.getElementById(id);
        if (element && element.id !== event.target.id) {
          element.checked = false;
        }
      });
    }
  }

  destroyChart() {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }
}

// Initialize the chart manager when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new ChartManager();
});

export default ChartManager;