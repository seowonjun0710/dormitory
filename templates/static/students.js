let csrfToken = "";

const esc = (str) => {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
};


async function api(url, options = {}) {
    if (!csrfToken) {
        const res = await fetch("/api/csrf");
        const ct = res.headers.get("content-type") || "";
        if (!ct.includes("application/json")) {
            throw new Error("로그인이 만료되었거나 서버 응답이 올바르지 않습니다. 새로고침해 주세요.");
        }
        csrfToken = (await res.json()).csrf_token;
    }
    const headers = { "X-CSRF-Token": csrfToken };
    if (options.body) headers["Content-Type"] = "application/json";

    const res = await fetch(url, { ...options, headers });
    const contentType = res.headers.get("content-type") || "";

    
    if (!contentType.includes("application/json")) {
        throw new Error("아직 서버에 연결되지 않은 기능이거나 로그인이 만료되었습니다.");
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "요청 실패");
    return data;
}

async function logout() {
    if (!csrfToken) {
        const res = await fetch("/api/csrf");
        csrfToken = (await res.json()).csrf_token;
    }
    const form = document.createElement("form");
    form.method = "POST";
    form.action = "/logout";

    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "csrf_token";
    input.value = csrfToken;

    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
}



function showSection(name, btn) {
    if (btn) {
        document.querySelectorAll("#top-nav button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    }

    document.querySelectorAll(".student-section").forEach(el => {
        el.style.display = "none";
    });
    const target = document.getElementById(`sec-${name}`);
    if (target) target.style.display = "block";

    if (name === "points") loadPointsAndAppeals();
    if (name === "repairs") loadRepairs();
}


document.addEventListener("DOMContentLoaded", () => {
    showSection("points");
});



async function loadPointsAndAppeals() {
    const pointsArea = document.getElementById("student-points-area");
    const formArea = document.getElementById("student-appeal-form-area");
    const appealsArea = document.getElementById("student-appeals-area");

    pointsArea.innerHTML = `<p>데이터를 불러오는 중...</p>`;

    try {
        const [pointsRes, appealsRes] = await Promise.all([
            api("/api/points"),
            api("/api/appeals")
        ]);

        const points = pointsRes.points || [];
        const appeals = appealsRes.appeals || [];

        const appealedPointIds = new Set(appeals.map(a => a.point_id));
        const appealablePenalties = points.filter(
            p => p.point_type === "penalty" && !appealedPointIds.has(p.id)
        );
        const statusText = { pending: "심사 대기", approved: "승인", rejected: "반려" };

        pointsArea.innerHTML = !points.length ? `<p>상벌점 기록이 없습니다.</p>` : `
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>번호</th>
                            <th>구분</th>
                            <th>점수</th>
                            <th>사유</th>
                            <th>일시</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${points.map(p => `
                            <tr>
                                <td>#${p.id}</td>
                                <td style="color:${p.point_type === "penalty" ? "#dc2626" : "#2563eb"}; font-weight:bold;">
                                    ${p.point_type === "penalty" ? "벌점" : "상점"}
                                </td>
                                <td>${p.amount}점</td>
                                <td>${esc(p.reason)}</td>
                                <td>${esc(p.created_at)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;


        formArea.innerHTML = !appealablePenalties.length
            ? `<p>이의제기를 신청할 수 있는 벌점 내역이 없습니다.</p>`
            : `
                <label for="appeal-point-id">이의제기할 벌점 선택</label>
                <select id="appeal-point-id">
                    ${appealablePenalties.map(p => `
                        <option value="${p.id}">
                            [#${p.id}] 벌점 ${p.amount}점 - ${esc(p.reason)} (${esc(p.created_at)})
                        </option>
                    `).join("")}
                </select>

                <label for="appeal-reason">이의제기 사유</label>
                <textarea id="appeal-reason" rows="3" maxlength="2000" placeholder="이의제기 사유를 구체적으로 작성하세요."></textarea>

                <button onclick="submitAppeal()" style="margin-top: 14px;">이의제기 제출</button>
            `;

       
        appealsArea.innerHTML = !appeals.length ? `<p>신청한 이의제기 내역이 없습니다.</p>` : `
            ${appeals.map(a => `
                <div class="list-row">
                    <p>
                        <strong>[기록 #${a.point_id}] ${a.point_type === "penalty" ? "벌점" : "상점"} ${a.amount}점</strong> | 
                        상태: <strong>${statusText[a.status] || a.status}</strong>
                    </p>
                    <p>내 신청 사유: ${esc(a.reason)}</p>
                    <p style="font-size:13px; color:#6b7280;">신청일: ${esc(a.created_at)}</p>
                    ${a.status !== "pending" ? `
                        <p style="background:#f4f5f7; padding:10px; border-radius:4px; margin-top:6px;">
                            <strong>관리자 심사 의견:</strong> ${esc(a.admin_comment)} (${esc(a.reviewed_at)})
                        </p>
                    ` : ""}
                </div>
            `).join("")}
        `;
    } catch (err) {
        pointsArea.innerHTML = `<p class="message">오류: ${esc(err.message)}</p>`;
    }
}

async function submitAppeal() {
    const point_id = Number(document.getElementById("appeal-point-id").value);
    const reason = document.getElementById("appeal-reason").value.trim();

    if (!point_id) return alert("이의제기할 벌점을 선택하세요.");
    if (!reason) return alert("이의제기 사유를 입력하세요.");

    try {
        const res = await api("/api/appeals", {
            method: "POST",
            body: JSON.stringify({ point_id, reason })
        });
        alert(res.message);
        loadPointsAndAppeals();
    } catch (err) {
        alert(err.message);
    }
}



async function loadRepairs() {
    const area = document.getElementById("student-repairs-area");
    area.innerHTML = `<p>데이터를 불러오는 중...</p>`;

    try {
        const res = await api("/api/repairs");
        const repairs = res.repairs || [];
        const statusText = { pending: "수리 대기", completed: "수리 완료" };
        document.getElementById("student-repairs-count").textContent = repairs.length;

        if (!repairs.length) {
            area.innerHTML = `<p>접수한 수리 요청 내역이 없습니다.</p>`;
            return;
        }

        area.innerHTML = `
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>번호</th>
                            <th>호실</th>
                            <th>학번 / 이름</th>
                            <th>고장 내용</th>
                            <th>상태</th>
                            <th>접수일 / 완료일</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${repairs.map(r => `
                            <tr>
                                <td>#${r.id}</td>
                                <td>${esc(r.room)}</td>
                                <td>${esc(r.student_number)} / ${esc(r.name)}</td>
                                <td>${esc(r.description)}</td>
                                <td style="color:${r.status === "completed" ? "#16a34a" : "#d97706"}; font-weight:bold;">
                                    ${statusText[r.status] || r.status}
                                </td>
                                <td>
                                    접수: ${esc(r.created_at)}
                                    ${r.completed_at ? `<br><span style="color:#16a34a; font-size:12px;">완료: ${esc(r.completed_at)}</span>` : ""}
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        area.innerHTML = `<p class="message">오류: ${esc(err.message)}</p>`;
    }
}

async function submitRepair() {
    const room = document.getElementById("rep-room").value.trim();
    const student_number = document.getElementById("rep-student-number").value.trim();
    const name = document.getElementById("rep-name").value.trim();
    const description = document.getElementById("rep-description").value.trim();

    if (!room) return alert("호실을 입력하세요.");
    if (!student_number) return alert("학번을 입력하세요.");
    if (!name) return alert("이름을 입력하세요.");
    if (!description) return alert("고장 내용을 입력하세요.");

    try {
        const res = await api("/api/repairs", {
            method: "POST",
            body: JSON.stringify({ room, student_number, name, description })
        });
        alert(res.message);
        document.getElementById("rep-room").value = "";
        document.getElementById("rep-student-number").value = "";
        document.getElementById("rep-name").value = "";
        document.getElementById("rep-description").value = "";
        loadRepairs();
    } catch (err) {
        alert(err.message);
    }
}

