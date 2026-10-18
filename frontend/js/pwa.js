// App instalable (PWA): registra el service worker (sw.js) y ofrece "Instalar app" en el menú.
// En Android/Chrome se usa el aviso de instalación del navegador; en iPhone/iPad se explica cómo hacerlo desde Safari.

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(error => console.error('No se pudo registrar el service worker:', error));
    });
}

let avisoInstalacion = null;

function appInstalada() {
    return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}

function esIOS() {
    // El iPad con iPadOS se presenta como Mac, pero tiene pantalla táctil
    return /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

function mostrarInstalar(mostrar) {
    const opcion = document.getElementById('instalar-app');
    if (opcion) opcion.hidden = !mostrar;
}

window.addEventListener('beforeinstallprompt', evento => {
    evento.preventDefault();  // se ofrece desde el menú, no como aviso automático
    avisoInstalacion = evento;
    mostrarInstalar(true);
});

window.addEventListener('appinstalled', () => {
    avisoInstalacion = null;
    mostrarInstalar(false);
});

document.addEventListener('DOMContentLoaded', () => {
    if (esIOS() && !appInstalada()) mostrarInstalar(true);
});

async function instalarApp() {
    if (avisoInstalacion) {
        avisoInstalacion.prompt();
        await avisoInstalacion.userChoice;
        avisoInstalacion = null;
        mostrarInstalar(false);
    } else if (esIOS()) {
        alert('Para instalar el campus en tu iPhone o iPad: en Safari toca el botón Compartir (el cuadro con la flecha hacia arriba) y elige "Agregar a pantalla de inicio".');
    }
}

window.instalarApp = instalarApp;
