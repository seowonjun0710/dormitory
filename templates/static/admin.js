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

    document.querySelectorAll(".admin-section").forEach(el => {
        el.style.display = "none";
    });
    const target = document.getElementById(`sec-${name}`);
    if (target) target.style.display = "block";

    if (name === "points") loadPoints();
    if (name === "appeals") loadAppeals();
    if (name === "repairs") loadRepairs();
    if (name === "cctv") loadCctvVideos();
    if (name === "rooms") loadRooms();
    if (name === "users") loadUsers();
}

document.addEventListener("DOMContentLoaded", () => {
    showSection("points");
});


async function loadPointsRanking() {
    const area = document.getElementById("points-ranking-area");
    if (!area) return;

    try {
        const res = await api("/api/admin/points/ranking");
        const winners = res.winners || [];
        const topReward = res.top_reward ?? 0;

        if (!winners.length || topReward <= 0) {
            area.innerHTML = `<span style="color:#6b7280;">최근 30일 이내 상점 획득 기록이 없습니다.</span>`;
            return;
        }

        const names = winners.map(w => `<strong>${esc(w.username)}</strong>`).join(", ");
        area.innerHTML = `
            🏆 현재 1위: ${names} 
            <span style="display:inline-block; margin-left:6px; padding:2px 8px; background:#e6f7f5; color:#0f766e; border-radius:999px; font-weight:700; font-size:12.5px;">
                누적 상점 +${topReward}점
            </span>
        `;
    } catch (err) {
        area.innerHTML = `<span style="color:#dc2626;">랭킹 조회 실패: ${esc(err.message)}</span>`;
    }
}


async function searchStudentPoints() {
    const inputEl = document.getElementById("search-point-username");
    const resultEl = document.getElementById("student-points-result");
    const username = inputEl ? inputEl.value.trim() : "";

    if (!username) {
        alert("학생 아이디를 입력하세요.");
        return;
    }

    resultEl.innerHTML = `<p style="color:#6b7280; font-size:13.5px;">조회 중...</p>`;

    try {
        const res = await api(`/api/admin/points/student?username=${encodeURIComponent(username)}`);
        const points = res.points || [];

        const summaryHtml = `
            <div style="display:flex; gap:14px; flex-wrap:wrap; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px 16px; margin-bottom:14px;">
                <div><strong>학생 ID:</strong> ${esc(res.username)}</div>
                <div style="color:#059669;"><strong>총 상점:</strong> +${res.total_reward}점</div>
                <div style="color:#dc2626;"><strong>총 벌점:</strong> -${res.total_penalty}점</div>
                <div style="color:#111827;"><strong>순수 합계:</strong> ${res.total_points >= 0 ? `+${res.total_points}` : res.total_points}점</div>
            </div>
        `;

        if (!points.length) {
            resultEl.innerHTML = summaryHtml + `<p style="color:#6b7280; font-size:13.5px;">등록된 상벌점 내역이 없습니다.</p>`;
            return;
        }

        const tableHtml = `
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>구분</th>
                            <th>점수</th>
                            <th>사유</th>
                            <th>일시</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${points.map(p => {
                            const isReward = p.point_type === "reward";
                            const badgeColor = isReward ? "#059669" : "#dc2626";
                            const typeLabel = isReward ? "상점" : "벌점";
                            const scoreText = isReward ? `+${p.amount}점` : `-${p.amount}점`;
                            return `
                                <tr>
                                    <td><strong style="color:${badgeColor};">${typeLabel}</strong></td>
                                    <td style="color:${badgeColor}; font-weight:600;">${scoreText}</td>
                                    <td>${esc(p.reason || "-")}</td>
                                    <td style="font-size:13px; color:#6b7280;">${esc(p.created_at || "")}</td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;

        resultEl.innerHTML = summaryHtml + tableHtml;
    } catch (err) {
        resultEl.innerHTML = `<p class="message">${esc(err.message)}</p>`;
    }
}


async function loadPoints() {
    loadPointsRanking(); 

    const area = document.getElementById("points-list-area");
    area.innerHTML = `<p>불러오는 중...</p>`;

    try {
        const res = await api("/api/admin/points");
        const points = res.points || [];
        document.getElementById("points-count").textContent = points.length;

        if (!points.length) {
            area.innerHTML = `<p>등록된 상벌점 내역이 없습니다.</p>`;
            return;
        }

        area.innerHTML = `
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>번호</th>
                            <th>학생</th>
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
                                <td>${esc(p.username || `ID:${p.student_id}`)}</td>
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
    } catch (err) {
        area.innerHTML = `<p class="message">오류: ${esc(err.message)}</p>`;
    }
}


async function givePoint() {
    const username = document.getElementById("pt-username").value.trim();
    const point_type = document.getElementById("pt-type").value;
    const amount = Number(document.getElementById("pt-amount").value);
    const reason = document.getElementById("pt-reason").value.trim();

    if (!username) return alert("학생 아이디를 입력하세요.");
    if (!amount || amount < 1 || amount > 100) return alert("점수를 1~100 사이로 입력하세요.");
    if (!reason) return alert("사유를 입력하세요.");

    try {
        const res = await api("/api/admin/points", {
            method: "POST",
            body: JSON.stringify({ username, point_type, amount, reason })
        });
        alert(res.message);
        document.getElementById("pt-username").value = "";
        document.getElementById("pt-reason").value = "";
        loadPoints(); 
    } catch (err) {
        alert(err.message);
    }
}


async function loadAppeals() {
    const area = document.getElementById("appeals-list-area");
    area.innerHTML = `<p>불러오는 중...</p>`;

    try {
        const res = await api("/api/admin/appeals");
        const appeals = (res.appeals || []).filter(a => a.status === "pending");
        document.getElementById("appeals-count").textContent = appeals.length;

        if (!appeals.length) {
            area.innerHTML = `<div class="menu-card"><p>심사 대기 중인 이의제기가 없습니다.</p></div>`;
            return;
        }

        area.innerHTML = appeals.map(a => `
            <div class="menu-card">
                <h3>#${a.id} 학생: ${esc(a.username)} (심사 대기)</h3>
                <p><strong>원래 내역:</strong> [${a.point_type === "penalty" ? "벌점" : "상점"} ${a.amount}점] ${esc(a.point_reason)}</p>
                <p><strong>이의제기 사유:</strong> ${esc(a.reason)}</p>
                <div style="margin-top: 12px;">
                    <input type="text" id="comment-${a.id}" maxlength="1000" placeholder="심사 의견 입력 (필수)">
                    <div style="margin-top: 10px; display:flex; gap:8px;">
                        <button onclick="reviewAppeal(${a.id}, 'approved')">승인</button>
                        <button onclick="reviewAppeal(${a.id}, 'rejected')" style="background:#dc2626;">반려</button>
                    </div>
                </div>
            </div>
        `).join("");
    } catch (err) {
        area.innerHTML = `<p class="message">오류: ${esc(err.message)}</p>`;
    }
}

async function reviewAppeal(id, status) {
    const comment = document.getElementById(`comment-${id}`).value.trim();
    if (!comment) return alert("심사 의견을 입력하세요.");

    try {
        const res = await api(`/api/admin/appeals/${id}/review`, {
            method: "POST",
            body: JSON.stringify({ status, admin_comment: comment })
        });
        alert(res.message);
        loadAppeals();
    } catch (err) {
        alert(err.message);
    }
}



async function loadRepairs() {
    const area = document.getElementById("repairs-list-area");
    area.innerHTML = `<p>불러오는 중...</p>`;

    try {
        const res = await api("/api/admin/repairs");
        const repairs = (res.repairs || []).filter(r => r.status === "pending");
        document.getElementById("repairs-count").textContent = repairs.length;

        if (!repairs.length) {
            area.innerHTML = `<div class="menu-card"><p>수리 대기 중인 요청이 없습니다.</p></div>`;
            return;
        }

        area.innerHTML = repairs.map(r => `
            <div class="menu-card">
                <h3>#${r.id} [${esc(r.room)}] ${esc(r.student_number)} ${esc(r.name)} (${esc(r.username)})</h3>
                <p><strong>고장 내용:</strong> ${esc(r.description)}</p>
                <p style="font-size:13px; color:#6b7280;">접수일: ${esc(r.created_at)}</p>
                <div style="margin-top: 12px;">
                    <button onclick="completeRepair(${r.id})">수리 완료</button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        area.innerHTML = `<p class="message">오류: ${esc(err.message)}</p>`;
    }
}

async function completeRepair(id) {
    try {
        const res = await api(`/api/admin/repairs/${id}/complete`, {
            method: "POST"
        });
        alert(res.message);
        loadRepairs();
    } catch (err) {
        alert(err.message);
    }
}



let activeStudentsCache = [];

async function loadRooms() {
    await Promise.all([
        fetchRoomList(),
        fetchActiveStudents()
    ]);
    await fetchExclusions();
}

async function fetchRoomList() {
    try {
        const res = await api("/api/admin/rooms");
        renderRoomCards(res.rooms || res.data || []);
    } catch (err) {
        renderRoomCards([], err.message);
    }
}

function renderRoomCards(rooms, infoMsg = "") {
    const infoEl = document.getElementById("rooms-info-msg");
    const gridEl = document.getElementById("room-grid");

    if (infoMsg) {
        infoEl.textContent = `* ${infoMsg}`;
        infoEl.style.display = "block";
    } else {
        infoEl.style.display = "none";
    }

    if (!rooms.length) {
        gridEl.innerHTML = `<div class="menu-card"><p style="color:#6b7280;">등록된 방이 없습니다. 위에서 방을 추가해 주세요.</p></div>`;
        return;
    }

    gridEl.innerHTML = rooms.map(r => {
        const roomNum = String(r.room_number ?? "");
        const capacity = r.capacity ?? 4;
        const students = r.students || r.occupants || [];

        return `
            <div class="menu-card" style="margin-bottom:0; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <h3 style="display:flex; justify-content:space-between; align-items:center;">
                        <span>${esc(roomNum)}호</span>
                        <span style="font-size:13px; color:#52b7ad; font-weight:600;">${students.length} / ${capacity}명</span>
                    </h3>
                    ${students.length === 0
                        ? `<p style="color:#9ca3af; font-size:14px;">배정된 학생이 없습니다.</p>`
                        : `<ul style="list-style:none; padding:0; margin:0;">
                            ${students.map((st, idx) => {
                                const displayName = st.username;

                                const grade = String(st.username || "")[0];

                                const meta = [
                                    ["1", "2", "3"].includes(grade) ? `${grade}학년` : "",
                                    st.gender || ""
                                ].filter(Boolean).join("/");
                                return `
                                    <li class="list-row">
                                        <strong>${idx + 1}번</strong> ${esc(displayName)}
                                        ${meta ? `<span style="font-size:12px; color:#6b7280;"> [${esc(meta)}]</span>` : ""}
                                    </li>
                                `;
                            }).join("")}
                           </ul>`
                    }
                </div>
                <div style="margin-top:14px; padding-top:10px; border-top:1px solid #f3f4f6; display:flex; gap:6px;">
                    <button onclick="renameRoom('${esc(roomNum)}')" style="flex:1; padding:6px 10px; font-size:12.5px; background:#4b5563;">번호 변경</button>
                    <button onclick="deleteRoom('${esc(roomNum)}')" style="flex:1; padding:6px 10px; font-size:12.5px; background:#dc2626;">방 삭제</button>
                </div>
            </div>
        `;
    }).join("");
}

async function addRoom() {
    const roomInput = document.getElementById("new-room-number");
    const room_number = roomInput.value.trim();

    if (!room_number) return alert("추가할 방 번호를 입력하세요.");

    try {
        const res = await api("/api/admin/rooms", {
            method: "POST",
            body: JSON.stringify({ room_number })
        });
        alert(res.message || `${room_number}호가 추가되었습니다.`);
        roomInput.value = "";
        fetchRoomList();
    } catch (err) {
        alert(err.message);
    }
}


async function renameRoom(oldRoomNumber) {
    const nextNumber = prompt(`${oldRoomNumber}호의 새 방 번호를 입력하세요:`, oldRoomNumber);
    if (!nextNumber || nextNumber.trim() === "" || nextNumber.trim() === oldRoomNumber) return;

    try {
        const res = await api(`/api/admin/rooms/${encodeURIComponent(oldRoomNumber)}`, {
            method: "PATCH",
            body: JSON.stringify({ new_room_number: nextNumber.trim() })
        });
        alert(res.message || "방 번호가 변경되었습니다.");
        loadRooms();
    } catch (err) {
        alert(err.message);
    }
}


async function deleteRoom(roomNumber) {
    if (!confirm(`${roomNumber}호를 정말 삭제하시겠습니까?`)) return;

    try {
        const res = await api(`/api/admin/rooms/${encodeURIComponent(roomNumber)}`, {
            method: "DELETE"
        });
        alert(res.message || `${roomNumber}호가 삭제되었습니다.`);
        loadRooms();
    } catch (err) {
        alert(err.message);
    }
}



async function runGroupRoomAllocation(grade, gender, btn) {
    const label = `${grade}학년 ${gender}학생`;
    if (!confirm(`${label} 그룹만 따로 랜덤 방 배정을 실행하시겠습니까?`)) return;

    const allBtns = document.querySelectorAll(".btn-group-allocate, #btn-allocate-rooms");
    const originText = btn ? btn.textContent : `${label} 배정`;

    allBtns.forEach(b => (b.disabled = true));
    if (btn) btn.textContent = "추첨 중...";

    try {
        await GachaAnimator.play(
            api("/api/admin/rooms/allocate", {
                method: "POST",
                body: JSON.stringify({ grade, gender })
            })
        );
        await loadRooms();
        GachaAnimator.animateCards("#room-grid .menu-card");
    } catch (err) {
        alert(err.message);
    } finally {
        allBtns.forEach(b => (b.disabled = false));
        if (btn) btn.textContent = originText;
    }
}

async function resetRooms() {
    if (!confirm("모든 학생의 방 배정 상태를 초기화하시겠습니까?")) return;

    try {
        const res = await api("/api/admin/rooms/reset", { method: "POST" });
        alert(res.message || "방 배정이 초기화되었습니다.");
        loadRooms();
    } catch (err) {
        alert(err.message);
    }
}

async function fetchActiveStudents() {
    try {
        const res = await api("/api/admin/rooms/students");
        activeStudentsCache = res.data || [];

        const optionsHtml = `<option value="">-- 학생 선택 --</option>` + activeStudentsCache.map(s => {
            const roomTag = s.room_number
                ? ` [${s.room_number}호]`
                : " [미배정]";

            const grade = String(s.username || "")[0];

            const meta = [
                ["1", "2", "3"].includes(grade) ? `${grade}학년` : "",
                s.gender || ""
            ].filter(Boolean).join("/");

            const nameText = s.username;
            return `<option value="${s.id}">${esc(`${nameText}${meta ? ` - ${meta}` : ""}${roomTag}`)}</option>`;
        }).join("");

        ["swap-student-1", "swap-student-2", "excl-student-1", "excl-student-2"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = optionsHtml;
        });
    } catch (err) {
        console.error("활성 학생 목록 조회 실패:", err.message);
    }
}

async function swapStudentRooms() {
    const student_id_1 = Number(document.getElementById("swap-student-1").value);
    const student_id_2 = Number(document.getElementById("swap-student-2").value);

    if (!student_id_1 || !student_id_2) return alert("교환할 두 학생을 모두 선택하세요.");
    if (student_id_1 === student_id_2) return alert("서로 다른 두 학생을 선택하세요.");

    try {
        const res = await api("/api/admin/rooms/swap", {
            method: "POST",
            body: JSON.stringify({ student_id_1, student_id_2 })
        });
        alert(res.message || "학생 방 교환이 완료되었습니다.");
        loadRooms();
    } catch (err) {
        alert(err.message);
    }
}

async function fetchExclusions() {
    const area = document.getElementById("exclusions-list-area");
    if (!area) return;

    try {
        const res = await api("/api/admin/rooms/exclusions");

        let list = [];
        if (Array.isArray(res)) {
            list = res;
        } else if (res && typeof res === "object") {
            list = res.exclusions || res.data || res.items || res.pairs || res.list
                || Object.values(res).find(v => Array.isArray(v))
                || [];
        }

        if (!list.length) {
            area.innerHTML = `<p style="font-size:13.5px; color:#6b7280;">등록된 금지 학생 쌍이 없습니다.</p>`;
            return;
        }

        const formatStudentLabel = (studentId, fallbackUsername) => {
            const st = activeStudentsCache.find(s => Number(s.id) === Number(studentId));
            const uname = st?.username || fallbackUsername || `ID:${studentId}`;
            const grade = String(uname)[0];
            const meta = [
                ["1", "2", "3"].includes(grade) ? `${grade}학년` : "",
                st?.gender || ""
            ].filter(Boolean).join("/");
            return meta ? `<strong>${esc(String(uname))}</strong> <span style="font-size:12px; color:#6b7280;">(${esc(meta)})</span>` : `<strong>${esc(String(uname))}</strong>`;
        };

        area.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:13px; font-weight:600; color:#374151;">등록된 금지 쌍 (${list.length}쌍)</span>
                <button onclick="clearAllExclusions()" style="padding:5px 10px; font-size:12px; background:#6b7280;">금지 쌍 전체 삭제</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>번호</th>
                            <th>학생 1</th>
                            <th>학생 2</th>
                            <th>관리</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${list.map((ex, idx) => {
                            const exId = ex.id ?? idx + 1;
                            const id1 = ex.student_id_1 ?? ex.student1_id ?? ex.user_id_1;
                            const id2 = ex.student_id_2 ?? ex.student2_id ?? ex.user_id_2;
                            const rawName1 = ex.username_1 || ex.student1_username || ex.student_name_1;
                            const rawName2 = ex.username_2 || ex.student2_username || ex.student_name_2;
                            return `
                                <tr>
                                    <td>#${esc(String(exId))}</td>
                                    <td>${formatStudentLabel(id1, rawName1)}</td>
                                    <td>${formatStudentLabel(id2, rawName2)}</td>
                                    <td>
                                        <button onclick="deleteExclusion(${Number(exId)})" style="padding:5px 10px; font-size:12.5px; background:#dc2626;">삭제</button>
                                    </td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        area.innerHTML = `<p class="message">금지 쌍 목록 오류: ${esc(err.message)}</p>`;
    }
}

async function addExclusion() {
    const student_id_1 = Number(document.getElementById("excl-student-1").value);
    const student_id_2 = Number(document.getElementById("excl-student-2").value);

    if (!student_id_1 || !student_id_2) return alert("금지 쌍으로 묶을 두 학생을 모두 선택하세요.");
    if (student_id_1 === student_id_2) return alert("서로 다른 두 학생을 선택하세요.");

    try {
        const res = await api("/api/admin/rooms/exclusions", {
            method: "POST",
            body: JSON.stringify({ student_id_1, student_id_2 })
        });
        alert(res.message || "금지 학생 쌍이 등록되었습니다.");
        fetchExclusions();
    } catch (err) {
        alert(err.message);
    }
}


async function deleteExclusion(id) {
    if (!confirm("이 금지 학생 쌍 설정을 삭제하시겠습니까?")) return;

    try {
        const res = await api(`/api/admin/rooms/exclusions/${id}`, {
            method: "DELETE"
        });
        alert(res.message || "삭제되었습니다.");
        fetchExclusions();
    } catch (err) {
        alert(err.message);
    }
}


async function clearAllExclusions() {
    if (!confirm("등록된 모든 금지 학생 쌍을 한 번에 삭제하시겠습니까?")) return;

    try {
        const res = await api("/api/admin/rooms/exclusions/clear", {
            method: "DELETE"
        });
        alert(res.message || "모든 금지 학생 쌍이 삭제되었습니다.");
        fetchExclusions();
    } catch (err) {
        alert(err.message);
    }
}


function formatDateTime(isoStr) {
    if (!isoStr) return "-";
    return isoStr.replace("T", " ").slice(0, 19);
}

async function loadCctvVideos() {
    const area = document.getElementById("cctv-list-area");
    area.innerHTML = `<p>감지 영상 목록을 불러오는 중...</p>`;

    try {
        const res = await api("/api/admin/cctv");
        const videos = res.videos || [];
        document.getElementById("cctv-count").textContent = videos.length;

        if (!videos.length) {
            area.innerHTML = `<p>보관 중인 CCTV 감지 영상이 없습니다.</p>`;
            return;
        }

        const eventLabel = { person: "사람 감지" };

        area.innerHTML = `
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>번호</th>
                            <th>감지 유형</th>
                            <th>행동 시작 시간</th>
                            <th>행동 종료 시간</th>
                            <th>자동 삭제 예정 시간</th>
                            <th>관리</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${videos.map(v => `
                            <tr>
                                <td>#${v.id}</td>
                                <td><strong>${esc(eventLabel[v.event_type] || v.event_type)}</strong></td>
                                <td>${esc(formatDateTime(v.start_time))}</td>
                                <td>${esc(formatDateTime(v.end_time))}</td>
                                <td style="color:#dc2626;">${esc(formatDateTime(v.expires_at))}</td>
                                <td style="display:flex; gap:6px; flex-wrap:wrap;">
                                    <button onclick="playCctvVideo(${v.id}, '${esc(formatDateTime(v.start_time))}')">재생</button>
                                    <a href="/api/admin/cctv/${v.id}/download" style="display:inline-block; padding:8px 14px; background:#374151; color:#fff; border-radius:6px; text-decoration:none; font-size:13.5px; font-weight:600;">다운로드</a>
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

function playCctvVideo(id, startTimeText) {
    const card = document.getElementById("cctv-player-card");
    const title = document.getElementById("cctv-player-title");
    const player = document.getElementById("cctv-video-player");

    title.textContent = `#${id} 감지 영상 재생 (${startTimeText})`;
    player.src = `/api/admin/cctv/${id}/video`;
    card.style.display = "block";
    player.play().catch(() => {});
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeCctvPlayer() {
    const card = document.getElementById("cctv-player-card");
    const player = document.getElementById("cctv-video-player");

    player.pause();
    player.removeAttribute("src");
    player.load();
    card.style.display = "none";
}


let studentUsersCache = [];

async function loadUsers() {
    const area = document.getElementById("users-list-area");
    if (!area) return;
    area.innerHTML = `<p>학생 계정 목록을 불러오는 중...</p>`;

    try {
        const res = await api("/api/admin/users");
        studentUsersCache = res.users || [];
        filterStudentUsers();
    } catch (err) {
        area.innerHTML = `<p class="message">오류: ${esc(err.message)}</p>`;
    }
}

function filterStudentUsers() {
    const keyword = (document.getElementById("search-user-student-id")?.value || "").trim();
    const filtered = keyword
        ? studentUsersCache.filter(u => String(u.username || "").includes(keyword))
        : studentUsersCache;

    const countEl = document.getElementById("users-count");
    if (countEl) countEl.textContent = filtered.length;

    renderStudentUsers(filtered);
}

function resetUserSearch() {
    const input = document.getElementById("search-user-student-id");
    if (input) input.value = "";
    filterStudentUsers();
}

function renderStudentUsers(users) {
    const area = document.getElementById("users-list-area");
    if (!area) return;

    if (!users.length) {
        area.innerHTML = `<p style="color:#6b7280;">일치하는 학생 계정이 없습니다.</p>`;
        return;
    }

    area.innerHTML = `
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>번호</th>
                        <th>학번 (아이디)</th>
                        <th>상태</th>
                        <th>가입일</th>
                        <th>관리</th>
                    </tr>
                </thead>
                <tbody>
                    ${users.map(u => `
                        <tr>
                            <td>#${u.id}</td>
                            <td><strong>${esc(u.username)}</strong></td>
                            <td>
                                <span style="color:${u.active ? "#059669" : "#6b7280"}; font-weight:600;">
                                    ${u.active ? "활성" : "비활성"}
                                </span>
                            </td>
                            <td style="font-size:13px; color:#6b7280;">${esc(u.created_at || "-")}</td>
                            <td>
                                <button onclick="deleteStudentUser(${u.id}, '${esc(u.username)}')" style="padding:6px 12px; font-size:12.5px; background:#dc2626;">
                                    삭제
                                </button>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function deleteStudentUser(userId, username) {
    if (!confirm(`학번 '${username}' 학생 계정을 정말 삭제하시겠습니까?\n삭제된 계정은 복구할 수 없습니다.`)) {
        return;
    }

    try {
        const res = await api(`/api/admin/users/${userId}/delete`, {
            method: "POST"
        });
        alert(res.message || "학생 계정이 삭제되었습니다.");
        await loadUsers();
    } catch (err) {
        alert(err.message);
    }
}