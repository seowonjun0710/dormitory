const GachaAnimator = (() => {
    function ensureStyle() {
        if (document.getElementById("roulette-anim-style")) return;

        const style = document.createElement("style");
        style.id = "roulette-anim-style";
        style.textContent = `
            #room-roulette-overlay {
                position: fixed;
                inset: 0;
                background: rgba(15, 23, 42, 0.84);
                backdrop-filter: blur(5px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            }
            .gacha-stage {
                position: relative;
                background: #ffffff;
                width: 92%;
                max-width: 440px;
                border-radius: 20px;
                padding: 28px 24px 32px;
                text-align: center;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.35);
                overflow: hidden;
            }
            .gacha-badge {
                display: inline-block;
                background: #e6f7f5;
                color: #0f766e;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.08em;
                padding: 4px 12px;
                border-radius: 999px;
                margin-bottom: 8px;
            }
            .gacha-title { margin: 0 0 4px; font-size: 21px; color: #111827; }
            .gacha-sub { margin: 0 0 20px; font-size: 13px; color: #6b7280; }
            .gacha-machine { position: relative; width: 190px; margin: 0 auto; }
            .gacha-dome {
                position: relative;
                width: 170px;
                height: 170px;
                margin: 0 auto;
                border-radius: 50%;
                background: radial-gradient(circle at 30% 30%, #ffffff, #e2e8f0 75%, #cbd5e1);
                border: 5px solid #52b7ad;
                box-shadow: inset 0 -10px 20px rgba(0,0,0,0.08), 0 8px 20px rgba(82,183,173,0.25);
                overflow: hidden;
            }
            .gacha-dome.shaking { animation: machineShake 0.14s infinite alternate; }
            .ball {
                position: absolute;
                width: 42px;
                height: 42px;
                border-radius: 50%;
                color: #fff;
                font-weight: 800;
                font-size: 13px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: inset -3px -3px 6px rgba(0,0,0,0.2);
            }
            .b1 { background: #ef4444; top: 25px; left: 30px; animation: bounce1 0.45s infinite alternate ease-in-out; }
            .b2 { background: #3b82f6; top: 70px; left: 95px; animation: bounce2 0.38s infinite alternate ease-in-out; }
            .b3 { background: #f59e0b; top: 95px; left: 35px; animation: bounce3 0.42s infinite alternate ease-in-out; }
            .b4 { background: #10b981; top: 30px; left: 90px; animation: bounce1 0.35s infinite alternate-reverse ease-in-out; }
            .b5 { background: #8b5cf6; top: 65px; left: 55px; animation: bounce2 0.32s infinite alternate-reverse ease-in-out; }
            .b6 { background: #ec4899; top: 105px; left: 85px; animation: bounce3 0.4s infinite alternate-reverse ease-in-out; }
            .gacha-cannon {
                width: 96px;
                height: 44px;
                margin: -12px auto 0;
                background: linear-gradient(180deg, #374151, #1f2937);
                border-radius: 8px 8px 18px 18px;
                position: relative;
                z-index: 2;
                display: flex;
                align-items: flex-end;
                justify-content: center;
                padding-bottom: 6px;
                box-shadow: 0 6px 14px rgba(0,0,0,0.25);
            }
            .cannon-mouth {
                width: 64px;
                height: 14px;
                background: #0f172a;
                border-radius: 999px;
                border: 2px solid #52b7ad;
            }
            .cannon-fire { animation: cannonRecoil 0.35s cubic-bezier(0.22, 1, 0.36, 1); }
            .launched-capsule {
                position: absolute;
                left: 50%;
                top: 62%;
                transform: translate(-50%, -50%) scale(0);
                width: 240px;
                border-radius: 28px;
                overflow: hidden;
                box-shadow: 0 18px 35px rgba(0,0,0,0.3);
                z-index: 10;
                opacity: 0;
                pointer-events: none;
            }
            .capsule-top {
                background: #52b7ad;
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                padding: 8px;
                letter-spacing: 0.06em;
            }
            .capsule-body {
                background: #ffffff;
                padding: 16px 12px;
                border: 3px solid #52b7ad;
                border-top: none;
                border-radius: 0 0 28px 28px;
            }
            #capsule-main-text { display: block; font-size: 20px; font-weight: 900; color: #111827; margin-bottom: 4px; }
            #capsule-sub-text { display: block; font-size: 12.5px; color: #4b5563; }
            .capsule-launch { animation: shootOut 0.65s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
            .confetti-container { position: absolute; left: 50%; top: 62%; z-index: 9; pointer-events: none; }
            .confetti-piece {
                position: absolute;
                width: 9px;
                height: 9px;
                border-radius: 2px;
                animation: confettiBurst 0.85s ease-out forwards;
            }
            @keyframes machineShake {
                0% { transform: rotate(-2.5deg) translateX(-2px); }
                100% { transform: rotate(2.5deg) translateX(2px); }
            }
            @keyframes bounce1 { 0% { transform: translate(0, 0) rotate(0deg); } 100% { transform: translate(45px, 65px) rotate(180deg); } }
            @keyframes bounce2 { 0% { transform: translate(0, 0) rotate(0deg); } 100% { transform: translate(-55px, -45px) rotate(-180deg); } }
            @keyframes bounce3 { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(40px, -65px) scale(1.1); } }
            @keyframes cannonRecoil {
                0% { transform: translateY(0) scaleY(1); }
                30% { transform: translateY(-10px) scaleY(0.82) scaleX(1.12); }
                100% { transform: translateY(0) scaleY(1); }
            }
            @keyframes shootOut {
                0% { opacity: 0; transform: translate(-50%, 10px) scale(0.15) rotate(-15deg); }
                60% { opacity: 1; transform: translate(-50%, -65%) scale(1.12) rotate(4deg); }
                100% { opacity: 1; transform: translate(-50%, -55%) scale(1) rotate(0deg); }
            }
            @keyframes confettiBurst {
                0% { opacity: 1; transform: translate(0, 0) scale(1) rotate(0deg); }
                100% { opacity: 0; transform: translate(var(--tx), var(--ty)) scale(0.4) rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }

    function spawnConfetti(container) {
        if (!container) return;
        const colors = ["#52b7ad", "#f59e0b", "#ef4444", "#3b82f6", "#10b981", "#8b5cf6"];
        for (let i = 0; i < 36; i++) {
            const dot = document.createElement("span");
            dot.className = "confetti-piece";
            const angle = (Math.PI * 2 * i) / 36;
            const dist = 90 + Math.random() * 140;
            dot.style.setProperty("--tx", `${Math.cos(angle) * dist}px`);
            dot.style.setProperty("--ty", `${Math.sin(angle) * dist - 40}px`);
            dot.style.background = colors[i % colors.length];
            container.appendChild(dot);
        }
    }

    async function play(apiPromise) {
        ensureStyle();

        const overlay = document.createElement("div");
        overlay.id = "room-roulette-overlay";
        overlay.innerHTML = `
            <div class="gacha-stage">
                <div class="gacha-badge">DORMITORY CAPSULE DRAW</div>
                <h2 id="gacha-status-title" class="gacha-title">추첨기 회전 중...</h2>
                <p id="gacha-status-sub" class="gacha-sub">금지 학생 쌍 조건을 피해 캡슐을 섞고 있습니다</p>
                <div class="gacha-machine">
                    <div id="gacha-dome" class="gacha-dome shaking">
                        <div class="ball b1">101</div><div class="ball b2">102</div>
                        <div class="ball b3">103</div><div class="ball b4">104</div>
                        <div class="ball b5">★</div><div class="ball b6">?</div>
                    </div>
                    <div id="gacha-cannon" class="gacha-cannon"><div class="cannon-mouth"></div></div>
                </div>
                <div id="launched-capsule" class="launched-capsule">
                    <div class="capsule-top">배정 완료</div>
                    <div class="capsule-body">
                        <span id="capsule-main-text">ALL ASSIGNED!</span>
                        <span id="capsule-sub-text">전체 호실 배정이 확정되었습니다</span>
                    </div>
                </div>
                <div id="confetti-container" class="confetti-container"></div>
            </div>
        `;
        document.body.appendChild(overlay);

        try {
            const [res] = await Promise.all([
                apiPromise,
                new Promise(resolve => setTimeout(resolve, 2200))
            ]);

            if (res.status === "error" || res.success === false) {
                throw new Error(res.message || "방 배정에 실패했습니다.");
            }

            document.getElementById("gacha-dome").classList.remove("shaking");
            document.getElementById("gacha-status-title").textContent = "캡슐 발사!";
            document.getElementById("gacha-status-sub").textContent = "배정 결과가 추출되었습니다!";
            document.getElementById("gacha-cannon").classList.add("cannon-fire");
            document.getElementById("launched-capsule").classList.add("capsule-launch");
            spawnConfetti(document.getElementById("confetti-container"));

            await new Promise(resolve => setTimeout(resolve, 1450));
            overlay.remove();
            return res;
        } catch (err) {
            overlay.remove();
            throw err;
        }
    }

    function animateCards(selector) {
        document.querySelectorAll(selector).forEach((card, idx) => {
            card.style.opacity = "0";
            card.style.transform = "translateY(24px) scale(0.92)";
            card.style.transition = "all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)";
            setTimeout(() => {
                card.style.opacity = "1";
                card.style.transform = "translateY(0) scale(1)";
            }, idx * 90);
        });
    }

    return { play, animateCards };
})();