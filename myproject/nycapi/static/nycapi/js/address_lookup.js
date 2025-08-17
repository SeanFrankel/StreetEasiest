/**
 * Renders a table for a given dataset, excluding any columns listed in excludedCols.
 * @param {Array} dataArray - The data to render
 * @param {string} title - The table title
 * @param {Array} excludedCols - Columns to exclude from the table
 * @param {Array} columnOrder - Optional array specifying the order of columns (columns not in this array will be appended at the end)
 */
function renderTable(dataArray, title, excludedCols = [], columnOrder = []) {
  if (!dataArray || !dataArray.length) {
    return `
      <div class="my-8 bg-grey-100 p-8 rounded-xl border border-grey-200">
        <h2 class="font-serif4 text-2xl md:text-3xl font-semibold mb-3 text-mackerel-400">${title}</h2>
        <p class="text-grey-600 font-sans3">No ${title} data available for this address.</p>
      </div>
    `;
  }
  
  // Determine columns from the keys of the first object, minus excludedCols
  let columns = Object.keys(dataArray[0]);
  columns = columns.filter(col => !excludedCols.includes(col));

  // Apply custom column ordering if provided
  if (columnOrder && columnOrder.length > 0) {
    // Create ordered columns array
    const orderedColumns = [];
    
    // Add columns in the specified order (if they exist in the data)
    columnOrder.forEach(col => {
      if (columns.includes(col)) {
        orderedColumns.push(col);
      }
    });
    
    // Add any remaining columns that weren't in the order array
    columns.forEach(col => {
      if (!orderedColumns.includes(col)) {
        orderedColumns.push(col);
      }
    });
    
    columns = orderedColumns;
  }

  const tableId = title.replace(/\s/g, '_');

  let html = `<div class="my-8" id="section-${tableId}">`;
  html += `<h2 class="font-serif4 text-2xl md:text-3xl font-semibold mb-4 text-mackerel-400">${title}</h2>`;
  html += `
    <div class="mb-4">
      <input
        type="text"
        class="form-input p-3 border border-grey-300 rounded-lg w-full sm:w-1/2 focus:ring-2 focus:ring-mackerel-200 focus:border-mackerel-300 transition font-sans3"
        placeholder="Filter ${title}..."
        onkeyup="filterTable(this, '${tableId}')"
      >
    </div>
  `;
  
  // Table controls for pagination with improved styling
  html += `
    <div class="mb-4 flex flex-wrap gap-3">
      <button 
        onclick="showMoreRows('${tableId}', 5)" 
        class="text-base bg-mackerel-200 hover:bg-mackerel-300 text-mackerel-800 py-3 px-6 rounded-lg transition font-sans3 font-medium shadow-sm flex items-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h10M4 14h16M4 18h10" />
        </svg>
        Show 5 Entries
      </button>
      <button 
        onclick="showMoreRows('${tableId}', 'all')" 
        class="text-base bg-mackerel-200 hover:bg-mackerel-300 text-mackerel-800 py-3 px-6 rounded-lg transition font-sans3 font-medium shadow-sm flex items-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        Show All Entries
      </button>
      <button 
        onclick="toggleTableVisibility('${tableId}')"
        id="toggle-${tableId}"
        class="text-base bg-mackerel-200 hover:bg-mackerel-300 text-mackerel-800 py-3 px-6 rounded-lg transition font-sans3 font-medium shadow-sm flex items-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
        </svg>
        Hide Table
      </button>
    </div>
  `;
  
  // Outer container with border and rounding
  html += `<div class="overflow-x-auto border border-grey-200 rounded-xl shadow-sm bg-white">`;
  
  // Table with collapsed borders, smaller padding
  html += `
    <table id="${tableId}" class="table-auto w-full border-collapse text-sm font-sans3">
      <thead class="bg-grey-100 border-b border-grey-200">
        <tr>
  `;
  columns.forEach(col => {
    html += `
      <th
        class="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase border border-gray-300"
      >
        ${col}
      </th>
    `;
  });
  html += `</tr></thead><tbody>`;

  // Rows with hover effect, smaller cell padding, borders on each cell
  dataArray.forEach((row, index) => {
    // Determine row styling based on data
    let rowClass = "hover:bg-gray-50 transition";
    
    // Check if this row has any issues (non-closed status or infested units)
    const hasIssues = columns.some(col => 
      (col === "violationstatus" && row[col] !== "Close") ||
      (col === "status" && row[col] !== "Closed") ||
      (col === "infested_dwelling_unit" && row[col] !== "0") ||
      (col === "casestatus" && row[col] !== "CLOSED")
    );
    
    // Debug logging
    console.log(`Row ${index}:`, { hasIssues, rowData: row });
    
    if (hasIssues) {
      rowClass += " bg-red-100";
      console.log(`Row ${index} should be RED`);
    } else {
      rowClass += " bg-green-100";
      console.log(`Row ${index} should be GREEN`);
    }
    
    // Add inline style as backup for debugging
    const inlineStyle = hasIssues ? 'background-color: #fee2e2;' : 'background-color: #dcfce7;';
    const displayStyle = index >= 5 ? 'display: none;' : '';
    const combinedStyle = `${inlineStyle} ${displayStyle}`;
    
    html += `<tr class="${rowClass}" data-row-index="${index}" style="${combinedStyle}">`;
    columns.forEach(col => {
      let value = row[col];
      // Check if the value is a valid ISO 8601 date string
      if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}$/.test(value)) {
        const date = new Date(value);
        if (!isNaN(date)) {
          // Get components for 12-hour time
          let hours = date.getHours();
          const minutes = String(date.getMinutes()).padStart(2, '0');
          const seconds = String(date.getSeconds()).padStart(2, '0');
          const ampm = hours >= 12 ? 'PM' : 'AM';
          hours = hours % 12 || 12; // Convert 0 to 12 for 12AM

          // Format as MM-DD-YYYY HH:mm:ss AM/PM
          const formattedDate = `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}-${date.getFullYear()} ${String(hours).padStart(2, '0')}:${minutes}:${seconds} ${ampm}`;
          value = formattedDate;
        }
      }

      html += `
        <td
          class="px-3 py-3 border border-gray-300 text-gray-700 whitespace-nowrap"
        >
          ${value !== undefined ? value : ""}
        </td>
      `;
    });    
    html += `</tr>`;
  });
  
  html += `</tbody></table></div>`;

  // Add "Jump to Top" button right under the table
  html += `
    <div class="mt-4 flex justify-end">
      <button 
        onclick="scrollToSection('data-summary')" 
        class="flex items-center text-mackerel-300 hover:text-mackerel-400 font-medium py-2 px-4 rounded-lg transition"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
        Back to Data Summary
      </button>
    </div>
  `;

  html += `</div>`;
  return html;
}

// Show more rows in a table
function showMoreRows(tableId, count) {
  const table = document.getElementById(tableId);
  const rows = table.getElementsByTagName("tbody")[0].getElementsByTagName("tr");
  
  if (count === 'all') {
    // Show all rows
    for (let i = 0; i < rows.length; i++) {
      rows[i].style.display = "";
    }
  } else {
    // Show only the specified number of rows
    for (let i = 0; i < rows.length; i++) {
      rows[i].style.display = i < count ? "" : "none";
    }
  }
}

// Toggle table visibility
function toggleTableVisibility(tableId) {
  const tableContainer = document.getElementById(tableId).closest('.overflow-x-auto');
  const toggleButton = document.getElementById(`toggle-${tableId}`);
  const isVisible = tableContainer.style.display !== 'none';
  
  if (isVisible) {
    tableContainer.style.display = 'none';
    toggleButton.textContent = 'Unhide Table';
  } else {
    tableContainer.style.display = 'block';
    toggleButton.textContent = 'Hide Table';
  }
}

// Filters table rows based on user input in the filter box
function filterTable(input, tableId) {
  const filter = input.value.toLowerCase();
  const table = document.getElementById(tableId);
  const rows = table.getElementsByTagName("tr");
  // Skip header row (index 0)
  for (let i = 1; i < rows.length; i++) {
    const rowText = rows[i].textContent.toLowerCase();
    rows[i].style.display = rowText.indexOf(filter) > -1 ? "" : "none";
  }
}

// Copy all table data to clipboard
function copyAllDataToClipboard() {
  const tables = document.querySelectorAll('table');
  let allData = '';
  
  tables.forEach(table => {
    const title = table.previousElementSibling.previousElementSibling.textContent;
    allData += `\n\n${title}\n`;
    
    // Get headers
    const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
    allData += headers.join('\t') + '\n';
    
    // Get rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
      const cells = Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim());
      allData += cells.join('\t') + '\n';
    });
  });
  
  navigator.clipboard.writeText(allData).then(() => {
    // Show a temporary success message
    const copyBtn = document.getElementById('copy-data-btn');
    const originalText = copyBtn.innerHTML;
    copyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg> Copied!';
    setTimeout(() => {
      copyBtn.innerHTML = originalText;
    }, 2000);
  });
}

// Scroll to a specific section
function scrollToSection(sectionId) {
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' });
  }
}

// DEBUG: Check if this file is loading
console.log("Address lookup JavaScript loaded!");

// Form submission event: fetch data with the X-Requested-With header
document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM loaded, setting up form listener");
  document.getElementById("lookup-form").addEventListener("submit", async function(event) {
    event.preventDefault();
    const address = document.getElementById("address").value.trim();
    const zipCode = document.getElementById("zip-code").value.trim();
    const resultsDiv = document.getElementById("results");
    const searchText = document.getElementById("search-text");
    const loadingSpinner = document.getElementById("loading-spinner");
    
    // Show loading state
    searchText.textContent = "Searching...";
    loadingSpinner.classList.remove("hidden");
    
    resultsDiv.innerHTML = `
      <div class="flex flex-col items-center justify-center p-4 bg-gray-100 rounded-lg border border-gray-200">
        <svg class="animate-spin h-5 w-5 text-blue-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-gray-700 text-sm">Searching...</p>
      </div>
    `;
    
    try {
      const response = await fetch(`/nyc-lookup-tool/?address=${encodeURIComponent(address)}&zip_code=${encodeURIComponent(zipCode)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });
      const data = await response.json();
      
      // DEBUG: Log the response to console
      console.log("API Response:", data);
      console.log("HPD Violations:", data.data?.hpd_violations?.length || "undefined");
      console.log("Complaints:", data.data?.complaints?.length || "undefined");
      
      // Reset button state
      searchText.textContent = "Search";
      loadingSpinner.classList.add("hidden");
      
      if (data.success) {
        // Create a data summary object to track available data
        const dataSummary = {
          hpd_violations: data.data.hpd_violations && data.data.hpd_violations.length > 0,
          complaints: data.data.complaints && data.data.complaints.length > 0,
          bedbug_reports: data.data.bedbug_reports && data.data.bedbug_reports.length > 0,
          litigation: data.data.litigation && data.data.litigation.length > 0,
          lead_paint_violations: data.data.lead_paint_violations && data.data.lead_paint_violations.length > 0,
          evictions: data.data.evictions && data.data.evictions.length > 0
        };
        
        // Count total records
        const totalRecords = Object.values(dataSummary).filter(Boolean).length;
        
        let html = `
          <div class="bg-white p-4 rounded-lg shadow border border-grey-200 mb-4">
            <h2 class="font-serif4 text-xl md:text-2xl font-semibold mb-3 text-mackerel-400">Property Information</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 font-sans3">
              <!-- Column 1: Basic Property Info -->
              <div class="space-y-2">
                <h3 class="font-medium text-grey-900 text-sm mb-3 border-b border-grey-200 pb-1">Basic Information</h3>
                <p class="text-sm"><span class="font-medium text-grey-800">Address:</span> <span class="text-grey-700">${data.data.address}</span></p>
                <p class="text-sm"><span class="font-medium text-grey-800">ZIP Code:</span> <span class="text-grey-700">${data.data.zip_code}</span></p>
                <p class="text-sm"><span class="font-medium text-grey-800">Building ID:</span> <span class="text-grey-700">${data.data.building_id || "N/A"}</span></p>
                <p class="text-sm"><span class="font-medium text-grey-800">BBL:</span> <span class="text-grey-700">${data.data.bbl || 'N/A'}</span></p>
                <p class="text-sm"><span class="font-medium text-grey-800">Total Residential Units:</span> <span class="text-grey-700">${data.data.residential_units ?? "N/A"}</span></p>
              </div>
              
              <!-- Column 2: Ownership & Building Info -->
              <div class="space-y-2">
                <h3 class="font-medium text-grey-900 text-sm mb-3 border-b border-grey-200 pb-1">Ownership Information</h3>
                <p class="text-sm"><span class="font-medium text-grey-800">Owner Name:</span> <span class="text-grey-700">${data.data.owner_name || "N/A"}</span></p>
                <p class="text-sm"><span class="font-medium text-grey-800">Owner Contact:</span> <span class="text-grey-700">${data.data.owner_contact || "N/A"}</span></p>
                ${(() => {
                  const regInfo = data.data.registration_info;
                  let regHtml = '';
                  
                  if (regInfo) {
                    if (regInfo.management_company) {
                      regHtml += `<p class="text-sm"><span class="font-medium text-grey-800">Management Company:</span> <span class="text-grey-700">${regInfo.management_company}</span></p>`;
                    }
                    
                    if (regInfo.registration_date) {
                      const regDate = new Date(regInfo.registration_date).toLocaleDateString();
                      regHtml += `<p class="text-sm"><span class="font-medium text-grey-800">Last HPD Registration:</span> <span class="text-grey-700">${regDate}</span></p>`;
                    }
                    
                    if (regInfo.year_built) {
                      regHtml += `<p class="text-sm"><span class="font-medium text-grey-800">Year Built:</span> <span class="text-grey-700">${regInfo.year_built}</span></p>`;
                    }
                  }
                  
                  return regHtml;
                })()}
              </div>
            </div>
          </div>
        `;
        
        // Add data summary section with integrated jump links
        html += `
          <div id="data-summary" class="bg-mackerel-200/10 p-4 rounded-lg border border-mackerel-200 mb-4">
            <h3 class="font-serif4 text-lg font-semibold mb-2 text-mackerel-400">Data Summary</h3>
            <p class="mb-3 text-sm text-grey-700 font-sans3">We found ${totalRecords} data sources for this address:</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Left Column: Violations, Reports, and Litigation -->
              <div class="space-y-2">
                <h4 class="font-medium text-grey-900 text-sm mb-3 border-b border-grey-200 pb-1">Violations & Reports</h4>
                
                <div class="flex items-center justify-between ${dataSummary.hpd_violations ? 'text-mackerel-300' : 'text-grey-400'} bg-white p-2 rounded border border-grey-200">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="font-sans3 font-medium text-sm">HPD Violations - Total: ${data.data.hpd_violations_total_count || 0}</span>
                  </div>
                  ${dataSummary.hpd_violations ? `
                    <button onclick="scrollToSection('section-HPD_Violations')" class="text-mackerel-300 hover:text-mackerel-400 text-xs font-medium font-sans3 flex items-center bg-mackerel-100 py-1 px-2 rounded transition">
                      View Data
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  ` : ''}
                </div>
                
                <div class="flex items-center justify-between ${dataSummary.complaints ? 'text-mackerel-300' : 'text-grey-400'} bg-white p-2 rounded border border-grey-200">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="font-sans3 font-medium text-sm">311 Complaints - Total: ${data.data.complaints_total_count || 0}</span>
                  </div>
                  ${dataSummary.complaints ? `
                    <button onclick="scrollToSection('section-311_Complaints')" class="text-mackerel-300 hover:text-mackerel-400 text-xs font-medium font-sans3 flex items-center bg-mackerel-100 py-1 px-2 rounded transition">
                      View Data
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  ` : ''}
                </div>
                
                <div class="flex items-center justify-between ${dataSummary.bedbug_reports ? 'text-mackerel-300' : 'text-grey-400'} bg-white p-2 rounded border border-grey-200">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="font-sans3 font-medium text-sm">Bedbug Reports - Total: ${data.data.bedbug_reports_total_count || 0}</span>
                  </div>
                  ${dataSummary.bedbug_reports ? `
                    <button onclick="scrollToSection('section-Bedbug_Reports')" class="text-mackerel-300 hover:text-mackerel-400 text-xs font-medium font-sans3 flex items-center bg-mackerel-100 py-1 px-2 rounded transition">
                      View Data
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  ` : ''}
                </div>
                
                <div class="flex items-center justify-between ${dataSummary.litigation ? 'text-mackerel-300' : 'text-grey-400'} bg-white p-2 rounded border border-grey-200">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="font-sans3 font-medium text-sm">Housing Litigation - Total: ${data.data.litigation_total_count || 0}</span>
                  </div>
                  ${dataSummary.litigation ? `
                    <button onclick="scrollToSection('section-Housing_Litigation')" class="text-mackerel-300 hover:text-mackerel-400 text-xs font-medium font-sans3 flex items-center bg-mackerel-100 py-1 px-2 rounded transition">
                      View Data
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  ` : ''}
                </div>
                
                <div class="flex items-center justify-between ${dataSummary.lead_paint_violations ? 'text-mackerel-300' : 'text-grey-400'} bg-white p-2 rounded border border-grey-200">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="font-sans3 font-medium text-sm">Lead Paint Violations - Total: ${data.data.lead_paint_violations_total_count || 0}</span>
                  </div>
                  ${dataSummary.lead_paint_violations ? `
                    <button onclick="scrollToSection('section-Lead_Paint_Violations')" class="text-mackerel-300 hover:text-mackerel-400 text-xs font-medium font-sans3 flex items-center bg-mackerel-100 py-1 px-2 rounded transition">
                      View Data
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  ` : ''}
                </div>
                
                <div class="flex items-center justify-between ${dataSummary.evictions ? 'text-red-600' : 'text-grey-400'} bg-white p-2 rounded border border-grey-200">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2V7zm0 0V5a2 2 0 012-2h6l2 2h6a2 2 0 012 2v2M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V9a2 2 0 012-2h2.586l.707-.707A2 2 0 0110.414 6H19a2 2 0 012 2v10a2 2 0 01-2 2h-8.586l-.707-.707z" />
                    </svg>
                    <span class="font-sans3 font-medium text-sm">Executed Evictions - Total: ${data.data.evictions_total_count || 0}</span>
                  </div>
                  ${dataSummary.evictions ? `
                    <button onclick="scrollToSection('section-Executed_Evictions')" class="text-red-600 hover:text-red-700 text-xs font-medium font-sans3 flex items-center bg-red-100 py-1 px-2 rounded transition">
                      View Data
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  ` : `
                    <span class="text-grey-400 bg-grey-100 text-xs font-medium font-sans3 py-1 px-2 rounded">
                      No Records
                    </span>
                  `}
                </div>
              </div>
              
              <!-- Right Column: Building & Rent Stabilization Information -->
              <div class="space-y-2">
                <h4 class="font-medium text-grey-900 text-sm mb-3 border-b border-grey-200 pb-1">Building Information</h4>
              
              ${(() => {
                // Add rent stabilization information (simplified single-tier approach)
                const hasStabilized = data.data.has_rent_stabilized === "Yes";
                const stabilizationReason = data.data.stabilization_reason;
                const units2023 = data.data.rent_stabilized_units_2023;
                const units2018 = data.data.rent_stabilized_units_2018;
                const unitsDifference = data.data.rent_stabilized_units_difference;
                const totalResidentialUnits = data.data.residential_units;
                
                let stabilizationHtml = '';
                
                // Add total residential units first
                if (totalResidentialUnits && totalResidentialUnits > 0) {
                  stabilizationHtml += `
                    <div class="flex items-center justify-between text-gray-600 bg-white p-2 rounded border border-grey-200">
                      <div class="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <span class="font-sans3 font-medium text-sm">Total Residential Units: ${totalResidentialUnits}</span>
                      </div>
                      <span class="text-gray-600 text-xs font-medium font-sans3 bg-gray-100 py-1 px-2 rounded">
                        Building Info
                      </span>
                    </div>
                  `;
                }
                
                // Add rent stabilization status lines for both years
                if (hasStabilized) {
                  // 2023 Data
                  if (units2023 && units2023 > 0) {
                    const percentage2023 = totalResidentialUnits ? Math.round((units2023 / totalResidentialUnits) * 100) : null;
                    const percentageText2023 = percentage2023 ? ` (${percentage2023}%)` : '';
                    
                    stabilizationHtml += `
                      <div class="flex items-center justify-between text-green-600 bg-white p-2 rounded border border-grey-200">
                        <div class="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span class="font-sans3 font-medium text-sm">Rent Stabilized Units (2023): ${units2023}${percentageText2023 ? ` - ${percentageText2023.replace('(', '').replace(')', '')} of building` : ''}</span>
                        </div>
                        <span class="text-green-600 text-xs font-medium font-sans3 bg-green-100 py-1 px-2 rounded">
                          Latest Data
                        </span>
                      </div>
                    `;
                  }
                  
                  // 2018 Data
                  if (units2018 && units2018 > 0) {
                    const percentage2018 = totalResidentialUnits ? Math.round((units2018 / totalResidentialUnits) * 100) : null;
                    const percentageText2018 = percentage2018 ? ` (${percentage2018}%)` : '';
                    
                    stabilizationHtml += `
                      <div class="flex items-center justify-between text-blue-600 bg-white p-2 rounded border border-grey-200">
                        <div class="flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span class="font-sans3 font-medium text-sm">Rent Stabilized Units (2018): ${units2018}${percentageText2018 ? ` - ${percentageText2018.replace('(', '').replace(')', '')} of building` : ''}</span>
                        </div>
                        <span class="text-blue-600 text-xs font-medium font-sans3 bg-blue-100 py-1 px-2 rounded">
                          Historical Data
                        </span>
                      </div>
                    `;
                  }
                  
                  // Change indicator
                  if (units2023 && units2018) {
                    const diff = units2023 - units2018;
                    const changeColor = diff > 0 ? 'text-green-700' : diff < 0 ? 'text-red-700' : 'text-grey-600';
                    const changeBg = diff > 0 ? 'bg-green-50 border-green-200' : diff < 0 ? 'bg-red-50 border-red-200' : 'bg-grey-50 border-grey-200';
                    const changeIcon = diff > 0 ? '↗' : diff < 0 ? '↘' : '→';
                    const changeText = diff > 0 ? `+${diff} units (increase)` : diff < 0 ? `${diff} units (decrease)` : 'No change';
                    
                    stabilizationHtml += `
                      <div class="flex items-center justify-between ${changeColor} ${changeBg} p-2 rounded border">
                        <div class="flex items-center">
                          <span class="text-lg mr-2">${changeIcon}</span>
                          <span class="font-sans3 font-medium text-sm">Rent Stabilized Units Change (2018→2023): ${changeText}</span>
                        </div>
                        <span class="${changeColor} text-xs font-medium font-sans3 py-1 px-2 rounded">
                          5-Year Trend
                        </span>
                      </div>
                    `;
                  }
                } else if (data.data.has_rent_stabilized === "No") {
                  stabilizationHtml += `
                    <div class="flex items-center justify-between text-red-600 bg-white p-2 rounded border border-grey-200">
                      <div class="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span class="font-sans3 font-medium text-sm">No Rent Stabilized Units Found</span>
                      </div>
                      <span class="text-red-600 text-xs font-medium font-sans3 bg-red-100 py-1 px-2 rounded">
                        NYCDB Data
                      </span>
                    </div>
                  `;
                } else {
                  // N/A case
                  stabilizationHtml += `
                    <div class="flex items-center justify-between text-grey-500 bg-white p-2 rounded border border-grey-200">
                      <div class="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span class="font-sans3 font-medium text-sm">Rent Stabilization Status</span>
                      </div>
                      <span class="text-grey-500 text-xs font-medium font-sans3 bg-grey-100 py-1 px-2 rounded">
                        Data Unavailable
                      </span>
                    </div>
                  `;
                }
                
                return stabilizationHtml;
              })()}
              </div>
            </div>
          </div>
        `;

        // Render HPD Violations with excluded columns and custom order
        const excludedColsForViolations = [
          "housenumber",
          "lowhousenumber",
          "highhousenumber",
          "streetname",
          "streetcode",
          "zip",
          "approveddate",
          "buildingid",
          "novissueddate",
          "registrationid",
          "boroid",
          "boro",
          "story",
          "block",
          "lot",
          "novtype",
          "latitude",
          "longitude",
          "communityboard",
          "councildistrict",
          "censustract",
          "bin",
          "bbl",
          "nta"
        ];
        
        // Define the order you want columns to appear in HPD Violations table
        const columnOrderForViolations = [
          "apartment",
          "inspectiondate",
          "rentimpairing",
          "class",
          "violationstatus",
          "novdescription",
          "currentstatus",
          "currentstatusdate",
          "originalcorrectbydate",
          "currentstatusid",
          "novid",
          "violationid",
          "originalcertifybydate"
        ];
        
        html += renderTable(data.data.hpd_violations, "HPD Violations", excludedColsForViolations, columnOrderForViolations);

        // Render 311 Complaints with excluded columns and custom order
        const excludedColsForComplaints = [
          "agency",
          "incident_zip",
          "incident_address",
          "street_name",
          "cross_street_1",
          "cross_street_2",
          "intersection_street_1",
          "intersection_street_2",
          "address_type",
          "city",
          "landmark",
          "resolution_action_updated_date",
          "community_board",
          "bbl",
          "borough",
          "x_coordinate_state_plane",
          "y_coordinate_state_plane",
          "open_data_channel_type",
          "park_facility_name",
          "park_borough",
          "latitude",
          "longitude",
          "location"
        ];
        
        // Define the order you want columns to appear in 311 Complaints table
        const columnOrderForComplaints = [
          "complaint_type",
          "descriptor",
          "created_date",
          "status",
          "resolution_description",
          "closed_date",
          "unique_key"
        ];
        
        html += renderTable(data.data.complaints, "311 Complaints", excludedColsForComplaints, columnOrderForComplaints);

        // Render Bedbug Reports with excluded columns and custom order
        const excludedColsForBedbugs = [
          "building_id",
          "registration_id",
          "borough",
          "house_number",
          "street_name",
          "postcode",
          "filling_period_end_date",
          "latitude",
          "longitude",
          "community_board",
          "city_council_district",
          "census_tract_2010",
          "bin",
          "bbl",
          "nta"
        ];
        
        // Define the order you want columns to appear in Bedbug Reports table
        const columnOrderForBedbugs = [
          "infested_dwelling_unit_count",
          "of_dwelling_units",
          "filing_period_start_date",
          "filing_date",
          "eradicated_unit_count",
          "re_infested_dwelling_unit"
        ];
        
        html += renderTable(data.data.bedbug_reports, "Bedbug Reports", excludedColsForBedbugs, columnOrderForBedbugs);

        // Render Housing Litigation with excluded columns and custom order
        const excludedColsForLitigation = [
          "buildingid",
          "boroid",
          "housenumber",
          "streetname",
          "zip",
          "block",
          "lot",
          "latitude",
          "longitude",
          "community_district",
          "council_district",
          "census_tract",
          "bin",
          "bbl",
          "nta"
        ];
        
        // Define the order you want columns to appear in Housing Litigation table
        const columnOrderForLitigation = [
          "casetype",
          "respondent",
          "caseopendate",
          "casestatus",
          "casejudgement",
          "litigationid"
        ];
        
        html += renderTable(data.data.litigation, "Housing Litigation", excludedColsForLitigation, columnOrderForLitigation);

        // Lead Paint Violations with excluded columns and custom order
        const excludedColsForLeadPaint = [
          "housenumber",
          "lowhousenumber", 
          "highhousenumber",
          "streetname",
          "streetcode",
          "zip",
          "boroid",
          "boro",
          "block",
          "lot",
          "bin",
          "bbl",
          "latitude",
          "longitude",
          "communityboard",
          "councildistrict",
          "censustract",
          "nta",
          "buildingid",
          "registrationid",
          "novtype",
          "ordernumber",
          "currentstatusid",
          "approveddate",
          "originalcertifybydate",
          "story",
          "class"
        ];
        
        // Define the order you want columns to appear in Lead Paint Violations table
        const columnOrderForLeadPaint = [
          "apartment",
          "inspectiondate",
          "novdescription", 
          "violationstatus",
          "currentstatus",
          "currentstatusdate",
          "violationid",
          "rentimpairing",
          "originalcorrectbydate",
          "novissueddate"
        ];
        
        html += renderTable(data.data.lead_paint_violations, "Lead Paint Violations", excludedColsForLeadPaint, columnOrderForLeadPaint);
        
        // Render Executed Evictions with excluded columns and custom order
        const excludedColsForEvictions = [
          "latitude",
          "longitude",
          "community_board",
          "council_district",
          "census_tract",
          "bin",
          "bbl",
          "nta",
          "borough",
          "eviction_zip",
          "court_index_number",
          "docket_number",
          "marshal_first_name",
          "marshal_last_name"
        ];
        
        // Define the order you want columns to appear in Evictions table (using actual API field names)
        const columnOrderForEvictions = [
          "eviction_address",
          "eviction_apt_num",
          "executed_date",
          "residential_commercial_ind",
          "eviction_possession",
          "ejectment"
        ];
        
        html += renderTable(data.data.evictions, "Executed Evictions", excludedColsForEvictions, columnOrderForEvictions);
        
        resultsDiv.innerHTML = html;
      } else {
        resultsDiv.innerHTML = `
          <div class="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl">
            <div class="flex items-center">
              <svg class="h-5 w-5 mr-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
              <p class="font-medium font-sans3">Error: ${data.error}</p>
            </div>
            <p class="mt-2 text-sm font-sans3">Please check your input and try again. Make sure you've entered a valid NYC address and ZIP code.</p>
          </div>
        `;
      }
    } catch (error) {
      // Reset button state
      searchText.textContent = "Search";
      loadingSpinner.classList.add("hidden");
      
      resultsDiv.innerHTML = `
        <div class="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl">
          <div class="flex items-center">
            <svg class="h-5 w-5 mr-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            <p class="font-medium font-sans3">An error occurred</p>
          </div>
          <p class="mt-2 text-sm font-sans3">${error.message || 'Please try again later or contact support if the problem persists.'}</p>
        </div>
      `;
    }
  });
}); 