const API_BASE_URL = process.env.REACT_APP_API_URL ||
  `${window.location.protocol}//${window.location.host}/api`;

console.log('API_BASE_URL:', API_BASE_URL);
console.log('window.location:', window.location.href);

export { API_BASE_URL };
