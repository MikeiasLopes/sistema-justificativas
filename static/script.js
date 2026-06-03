const canvas = document.getElementById("canvasAssinatura");
const ctx = canvas.getContext("2d");

let desenhando = false;
let assinou = false;

function ajustarCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#000";
}

window.addEventListener("resize", ajustarCanvas);
ajustarCanvas();

function pegarPosicao(evento) {
    const rect = canvas.getBoundingClientRect();

    if (evento.touches && evento.touches.length > 0) {
        return {
            x: evento.touches[0].clientX - rect.left,
            y: evento.touches[0].clientY - rect.top
        };
    }

    return {
        x: evento.clientX - rect.left,
        y: evento.clientY - rect.top
    };
}

function iniciarDesenho(evento) {
    evento.preventDefault();
    desenhando = true;
    assinou = true;

    const pos = pegarPosicao(evento);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
}

function desenhar(evento) {
    if (!desenhando) return;

    evento.preventDefault();
    const pos = pegarPosicao(evento);

    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
}

function pararDesenho(evento) {
    evento.preventDefault();
    desenhando = false;
}

function limparAssinatura() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    assinou = false;
}

function prepararAssinatura() {
    if (!assinou) {
        alert("Por favor, faça sua assinatura antes de enviar.");
        return false;
    }

    const assinatura = canvas.toDataURL("image/png");
    document.getElementById("assinatura").value = assinatura;

    return true;
}

canvas.addEventListener("mousedown", iniciarDesenho);
canvas.addEventListener("mousemove", desenhar);
canvas.addEventListener("mouseup", pararDesenho);
canvas.addEventListener("mouseleave", pararDesenho);

canvas.addEventListener("touchstart", iniciarDesenho);
canvas.addEventListener("touchmove", desenhar);
canvas.addEventListener("touchend", pararDesenho);
