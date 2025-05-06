const session_id = 'sesion1'; // Puedes usar UUID en producción

document.getElementById('btnUpload').addEventListener('click', async () => {
  const file = document.getElementById('pdfUpload').files[0];
  if (!file) return alert('Selecciona un archivo PDF primero.');

  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', session_id);

  const res = await fetch('/upload-iso', {
    method: 'POST',
    body: formData
  });

  const data = await res.json();
  alert(data.message || data.error);
});

document.getElementById('btnObtener').addEventListener('click', async () => {
  const caso = document.getElementById('idcaso').value;
  if (!caso.trim()) return alert('Escribe un caso práctico.');

  const res = await fetch('/analyze-case', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ caso, session_id })
  });

  const data = await res.json();
  if (data.analysis) {
    document.getElementById('resia').value = data.analysis;
  } else {
    alert(data.error);
  }
});

document.getElementById('btnEvaluar').addEventListener('click', async () => {
  const userResponse = document.getElementById('respropia').value;
  if (!userResponse.trim()) return alert('Escribe tu análisis propio.');

  const res = await fetch('/evaluate-response', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userResponse, session_id })
  });

  const data = await res.json();
  if (data.calificacionIA !== undefined) {
    document.getElementById('calIA').textContent = data.calificacionIA;
    document.getElementById('calUsuario').textContent = data.calificacionUsuario;
    document.getElementById('confIA').textContent = data.confianzaIA;
    document.getElementById('confUsuario').textContent = data.confianzaUsuario;
    document.getElementById('comentarioGeneral').textContent = data.comentarioGeneral;

    const modal = new bootstrap.Modal(document.getElementById('modalEvaluacion'));
    modal.show();
  } else {
    alert(data.error || 'Ocurrió un error al evaluar la respuesta.');
  }
});
