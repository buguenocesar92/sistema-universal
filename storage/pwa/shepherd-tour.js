// shepherd-tour.js — Tour guiado primera vez para usuarios nuevos
// Se activa si localStorage.kraftdo_tour_completed !== "true"

(function() {
  if (localStorage.getItem('kraftdo_tour_completed') === 'true') return;

  // Cargar Shepherd.js dinamicamente (CDN)
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://cdn.jsdelivr.net/npm/shepherd.js@11/dist/css/shepherd.css';
  document.head.appendChild(link);

  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/shepherd.js@11/dist/js/shepherd.min.js';
  script.onload = iniciarTour;
  document.head.appendChild(script);

  function iniciarTour() {
    const tour = new Shepherd.Tour({
      useModalOverlay: true,
      defaultStepOptions: {
        classes: 'shepherd-kraftdo',
        scrollTo: { behavior: 'smooth', block: 'center' },
        cancelIcon: { enabled: true },
      },
    });

    tour.addStep({
      title: '¡Bienvenido a KraftDo!',
      text: 'Este portal te permite subir tu Excel mensual y recibir el reporte por correo automaticamente. Toma 30 segundos aprenderlo.',
      buttons: [{ text: 'Empezar', action: tour.next, classes: 'shepherd-button-primary' }],
    });

    tour.addStep({
      title: 'Paso 1 — Selecciona tu empresa',
      text: 'Elige la empresa de la que quieres enviar el reporte.',
      attachTo: { element: '#empresa', on: 'bottom' },
      buttons: [
        { text: 'Atras', action: tour.back, secondary: true },
        { text: 'Siguiente', action: tour.next },
      ],
    });

    tour.addStep({
      title: 'Paso 2 — Codigo de acceso',
      text: 'Ingresa el codigo que te dio KraftDo. Es unico por cliente.',
      attachTo: { element: '#token', on: 'bottom' },
      buttons: [
        { text: 'Atras', action: tour.back, secondary: true },
        { text: 'Siguiente', action: tour.next },
      ],
    });

    tour.addStep({
      title: 'Paso 3 — Sube el Excel',
      text: 'Arrastra tu archivo aqui o haz clic para seleccionarlo. Solo .xlsx o .xls, maximo 10MB.',
      attachTo: { element: '#dropZone', on: 'top' },
      buttons: [
        { text: 'Atras', action: tour.back, secondary: true },
        { text: 'Siguiente', action: tour.next },
      ],
    });

    tour.addStep({
      title: '¡Listo!',
      text: 'En pocos minutos vas a recibir el reporte por correo. Si tienes dudas, escribe a hola@kraftdo.cl',
      buttons: [{
        text: 'Entendido',
        classes: 'shepherd-button-primary',
        action: () => {
          localStorage.setItem('kraftdo_tour_completed', 'true');
          tour.complete();
        }
      }],
    });

    setTimeout(() => tour.start(), 500);
  }
})();
