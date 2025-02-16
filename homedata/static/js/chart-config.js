import { DataTypes, BedroomTypes } from './data-types.js';

// Configuration constants
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
      dataType: DataTypes.MEDIAN,
      bedroom: BedroomTypes.ALL,
      neighborhood: 'Manhattan'
    },
    chartDefaults: {
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
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 15
          }
        }
      },
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
    }
  };
  
  export default CHART_CONFIG;