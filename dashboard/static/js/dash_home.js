document.addEventListener("DOMContentLoaded", () => {
    // Brand Colors
    const socBlueDark = "#2A4B8C";
    const socBlueMedium = "#6B8EBF";
    const socBlueLight = "#9DBBDD";
    const socGreen = "#28a745";

    // === Sales Week Chart ===
    const salesWeekCard = document.getElementById('salesWeekChartCard');
    if (salesWeekCard) {
        const salesWeekCtx = document.getElementById('salesWeekChart').getContext('2d');
        
        let weekLabels = [];
        let weekSales = [];
        try {
            const labelsData = salesWeekCard.dataset.bsLabels;
            const valuesData = salesWeekCard.dataset.bsValues;
            
            weekLabels = JSON.parse(labelsData || '[]');
            weekSales = JSON.parse(valuesData || '[]');
        } catch (e) {
            console.error("Error parsing sales chart data:", e);
        }

        new Chart(salesWeekCtx, {
            type: 'line',
            data: {
                labels: weekLabels,
                datasets: [{
                    label: 'Sales',
                    data: weekSales,
                    fill: true,
                    backgroundColor: 'rgba(42, 75, 140, 0.1)',
                    borderColor: socBlueDark,
                    borderWidth: 3,
                    pointBackgroundColor: socBlueDark,
                    pointBorderColor: "#fff",
                    pointHoverRadius: 6,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        padding: 10,
                        backgroundColor: '#fff',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: '#eee',
                        borderWidth: 1,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return context.parsed.y.toLocaleString() + ' DZD';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { drawBorder: false, color: 'rgba(0,0,0,0.05)' },
                        ticks: { color: '#888' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#888' }
                    }
                }
            }
        });
    }

    // === Top Products Chart ===
    const topProductsCard = document.getElementById('topProductsChartCard');
    if (topProductsCard) {
        const topProductsCtx = document.getElementById('topProductsChart').getContext('2d');
        
        let topProductsLabels = [];
        let topProductsValues = [];
        try {
            topProductsLabels = JSON.parse(topProductsCard.dataset.bsLabels || '[]');
            topProductsValues = JSON.parse(topProductsCard.dataset.bsValues || '[]');
        } catch (e) {
            console.error("Error parsing products chart data:", e);
        }

        new Chart(topProductsCtx, {
            type: 'bar',
            data: {
                labels: topProductsLabels,
                datasets: [{
                    label: 'Qty',
                    data: topProductsValues,
                    backgroundColor: socBlueMedium,
                    borderRadius: 8,
                    hoverBackgroundColor: socBlueDark,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { padding: 10 }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { display: false },
                        ticks: { color: '#888' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#888' }
                    }
                }
            }
        });
    }

    // === User Distribution Chart (Admin Only) ===
    const userDistCard = document.getElementById('userDistChartCard');
    if (userDistCard) {
        const userDistCtx = document.getElementById('userDistChart').getContext('2d');
        
        let userLabels = [];
        let userValues = [];
        try {
            userLabels = JSON.parse(userDistCard.dataset.bsLabels || '[]');
            userValues = JSON.parse(userDistCard.dataset.bsValues || '[]');
        } catch (e) {
            console.error("Error parsing user distribution data:", e);
        }

        new Chart(userDistCtx, {
            type: 'doughnut',
            data: {
                labels: userLabels,
                datasets: [{
                    data: userValues,
                    backgroundColor: [socBlueDark, socBlueLight],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: { size: 12, family: 'Cairo' }
                        }
                    },
                    tooltip: {
                        padding: 12,
                        backgroundColor: '#fff',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: '#eee',
                        borderWidth: 1,
                        displayColors: true,
                        boxPadding: 6
                    }
                }
            }
        });
    }
});
