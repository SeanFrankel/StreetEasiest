class FetchError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'FetchError';
    this.status = status;
  }
}

class DataFetcher {
  static async fetchRentalData({ dataType, bedroom, area, seasonal }) {
    const url = new URL('/homedata/rental-data-json/', window.location.origin);
    url.searchParams.set('data', dataType);
    url.searchParams.set('bedrooms', bedroom);
    url.searchParams.set('area', area);
    url.searchParams.set('seasonal', seasonal);

    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json();
        throw new FetchError(
          errorData.error || 'Failed to fetch data',
          response.status
        );
      }
      const data = await response.json();
      return { dataType, bedroom, area, data };
    } catch (error) {
      console.error(`Error fetching data: ${error.message}`);
      throw error;
    }
  }

  static async fetchMultipleDatasets(selections) {
    const requests = [];
    const { dataTypes, bedrooms, neighborhoods, useSeasonalData } = selections;

    for (const dt of dataTypes) {
      for (const bed of bedrooms) {
        for (const nb of neighborhoods) {
          requests.push(
            this.fetchRentalData({
              dataType: dt,
              bedroom: bed,
              area: nb,
              seasonal: useSeasonalData
            })
          );
        }
      }
    }

    try {
      return await Promise.all(requests);
    } catch (error) {
      console.error('Error fetching multiple datasets:', error);
      throw error;
    }
  }
}

export { DataFetcher, FetchError };