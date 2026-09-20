document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/analytics')
    .then(response => response.json())
    .then(data => {
      // 1. Complaints By Building (Bar Chart)
      new Chart(document.getElementById('buildingChart'), {
        type: 'bar',
        data: {
          labels: data.buildings,
          datasets: [{
            data: data.building_data,
            backgroundColor: '#f59e0b',
            borderRadius: 4,
            barThickness: 24
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
          }
        }
      });

      // 2. Complaints Per Month (Curved Line Chart)
      new Chart(document.getElementById('monthlyChart'), {
        type: 'line',
        data: {
          labels: data.months,
          datasets: [{
            data: data.monthly_data,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: '#38bdf8',
            fill: true
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
          }
        }
      });

      // 3. Repair Cost By Category (Green Bar Chart)
      new Chart(document.getElementById('costChart'), {
        type: 'bar',
        data: {
          labels: data.categories,
          datasets: [{
            data: data.category_costs,
            backgroundColor: '#10b981',
            borderRadius: 4,
            barThickness: 28
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: {
                color: '#94a3b8',
                callback: (value) => '₹' + value
              }
            },
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
          }
        }
      });
    });
});