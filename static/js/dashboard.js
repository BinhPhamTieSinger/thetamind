document.addEventListener('DOMContentLoaded', () => {
    const statsDataEl = document.getElementById('stats-data');
    if (!statsDataEl) return;

    const stats = JSON.parse(statsDataEl.innerHTML);
    if (!stats || stats.length === 0) return;

    // --- Process data for charts ---
    const topicData = {};
    let totalCorrect = 0;
    let totalIncorrect = 0;

    stats.forEach(stat => {
        if (!topicData[stat.topic]) {
            topicData[stat.topic] = { correct: 0, incorrect: 0 };
        }
        if (stat.is_correct) {
            topicData[stat.topic].correct += stat.count;
            totalCorrect += stat.count;
        } else {
            topicData[stat.topic].incorrect += stat.count;
            totalIncorrect += stat.count;
        }
    });

    const topicLabels = Object.keys(topicData);
    const correctData = topicLabels.map(topic => topicData[topic].correct);
    const incorrectData = topicLabels.map(topic => topicData[topic].incorrect);
    
    const isDarkMode = !document.body.classList.contains('light-mode');
    const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    const textColor = isDarkMode ? '#e0e0e0' : '#333';


    // --- Chart 1: Topic Performance (Stacked Bar) ---
    const topicCtx = document.getElementById('topicPerformanceChart')?.getContext('2d');
    if (topicCtx) {
        new Chart(topicCtx, {
            type: 'bar',
            data: {
                labels: topicLabels,
                datasets: [
                    {
                        label: 'Correct',
                        data: correctData,
                        backgroundColor: 'rgba(0, 247, 255, 0.7)', // accent
                        borderColor: 'rgba(0, 247, 255, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Incorrect',
                        data: incorrectData,
                        backgroundColor: 'rgba(255, 0, 255, 0.7)', // secondary accent
                        borderColor: 'rgba(255, 0, 255, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { labels: { color: textColor } },
                    title: { display: false }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: { color: gridColor },
                        ticks: { color: textColor }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { color: textColor }
                    }
                }
            }
        });
    }

    // --- Chart 2: Overall Accuracy (Doughnut) ---
    const accuracyCtx = document.getElementById('overallAccuracyChart')?.getContext('2d');
    if (accuracyCtx) {
        new Chart(accuracyCtx, {
            type: 'doughnut',
            data: {
                labels: ['Correct', 'Incorrect'],
                datasets: [{
                    data: [totalCorrect, totalIncorrect],
                    backgroundColor: [
                        'rgba(0, 247, 255, 0.8)',
                        'rgba(255, 0, 255, 0.8)'
                    ],
                    borderColor: [
                        '#0d0d2b'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                     legend: { position: 'top', labels: { color: textColor } },
                     title: { display: false }
                }
            }
        });
    }
});
