document.addEventListener('DOMContentLoaded', () => {

    // --- Theme Toggler ---
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // Apply the cached theme on load
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        body.classList.add(savedTheme);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
        // If no theme is saved, check user's OS preference
        body.classList.add('light-mode');
    }

    themeToggle.addEventListener('click', () => {
        body.classList.toggle('light-mode');
        // Save the new theme preference
        if (body.classList.contains('light-mode')) {
            localStorage.setItem('theme', 'light-mode');
        } else {
            localStorage.removeItem('theme');
        }
    });

    // --- Matrix Background Animation on Banner ---
    const matrixBackground = document.getElementById('matrix-background');
    if (matrixBackground) {
        const canvas = document.createElement('canvas');
        matrixBackground.appendChild(canvas);
        const ctx = canvas.getContext('2d');

        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;
        let columns = Math.floor(width / 20);
        const drops = [];

        for (let i = 0; i < columns; i++) {
            drops[i] = 1;
        }

        const characters = '0123456789ABCDEFΓΔΘΛΞΠΣΦΨΩαβγδεζηθικλμνξπρστυφχψω';

        function drawMatrix() {
            ctx.fillStyle = 'rgba(13, 13, 43, 0.05)';
            ctx.fillRect(0, 0, width, height);
            ctx.fillStyle = '#00f7ff'; // Cyan color for the characters
            ctx.font = '15px monospace';

            for (let i = 0; i < drops.length; i++) {
                const text = characters.charAt(Math.floor(Math.random() * characters.length));
                ctx.fillText(text, i * 20, drops[i] * 20);

                if (drops[i] * 20 > height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            }
        }

        let interval = setInterval(drawMatrix, 40);

        window.addEventListener('resize', () => {
             width = canvas.width = window.innerWidth;
             height = canvas.height = window.innerHeight;
             columns = Math.floor(width / 20);
             drops.length = 0; // Clear the array
             for (let i = 0; i < columns; i++) {
                drops[i] = 1;
             }
        });
    }
});
