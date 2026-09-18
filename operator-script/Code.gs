/**
 * 교육과정 박람회 · 운영자 접수 스크립트  (v1)
 * ----------------------------------------------------------------------
 * 하나의 앱스크립트가 모든 학교의 다음 요청을 처리합니다.
 *   - register : 학교 선생님의 "결과 수집 신청" (사이트 신청 폼 → 운영 시트 '학교' 탭에 대기 행 추가)
 *   - submit   : 학생의 체크리스트 결과 제출 (승인된 학교의 시트에 기록)
 *   - status   : 사이트가 "이 학교는 제출 가능한가?"를 물어보는 조회 (GET)
 *
 * 운영자가 하는 일: 운영 시트 '학교' 탭에서 상태를 '승인'으로 바꾸고 메뉴 [승인 처리 실행]을 누르면
 * 학교별 결과 시트가 자동으로 만들어지고, 담당 선생님 이메일에 편집자로 공유 + 안내 메일이 갑니다.
 *
 * 설치 순서는 README-운영자.md 참고.
 */

// ===================== 설정 =====================
const CONFIG = {
  SITE_NAME: "2026 교육과정 박람회",
  SITE_URL: "https://wade-afk.github.io/2026-curriculum-fair/",   // 학교 링크 안내용
  OPERATOR_NAME: "박람회 운영자",                                    // 메일 서명
  RESULT_FOLDER_NAME: "교육과정박람회_학교별결과",                     // 운영자 드라이브에 만들 폴더
  TEMPLATE_SPREADSHEET_ID: "",   // (선택) 학교 시트를 이 템플릿의 사본으로 만들려면 ID 입력. 비우면 기본 형식으로 새로 생성
  TRANSFER_OWNERSHIP: false,     // true면 학교 시트 소유권을 담당 선생님에게 넘김 (구글 Workspace 계정 간에만 동작)
  SHEET_SCHOOLS: "학교",
  SHEET_LOG: "로그",
};

const SCHOOL_COLS = ["학교ID","학교명","지역","구·군","담당자","이메일","연락처","상태","시트URL","신청시각","승인시각","제출수","메모","전용주소","QR이미지"];
const STATUS = { WAIT:"대기", OK:"승인", STOP:"중지" };

// ===================== 메뉴 =====================
function onOpen(){
  SpreadsheetApp.getUi().createMenu("🎓 박람회 운영")
    .addItem("1. 초기 설정 (탭 만들기)", "setup")
    .addItem("2. 승인 처리 실행 (상태=승인 → 시트 생성·공유·메일)", "processApprovals")
    .addItem("3. 웹 앱 URL 확인", "showWebAppUrl")
    .addSeparator()
    .addItem("승인 자동 처리 켜기 (편집 시 자동 실행)", "installEditTrigger")
    .addItem("제출 수 새로고침", "refreshCounts")
    .addItem("안내 메일 다시 보내기 (주소·QR 포함, 선택한 행)", "resendApprovalMail")
    .addToUi();
}

/** 운영 시트에 '학교'·'로그' 탭을 만듭니다. 여러 번 실행해도 안전합니다. */
function setup(){
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(CONFIG.SHEET_SCHOOLS);
  if(sh){ // 기존 탭이면 새 열 머리글 보강
    sh.getRange(1,1,1,SCHOOL_COLS.length).setValues([SCHOOL_COLS]).setFontWeight("bold").setBackground("#F2F4F9");
    sh.setColumnWidth(14, 320);
  }
  if(!sh){
    sh = ss.insertSheet(CONFIG.SHEET_SCHOOLS);
    sh.getRange(1,1,1,SCHOOL_COLS.length).setValues([SCHOOL_COLS]).setFontWeight("bold").setBackground("#F2F4F9");
    sh.setFrozenRows(1);
    sh.setColumnWidth(2, 160); sh.setColumnWidth(6, 220); sh.setColumnWidth(9, 320);
    const rule = SpreadsheetApp.newDataValidation().requireValueInList([STATUS.WAIT,STATUS.OK,STATUS.STOP], true).build();
    sh.getRange(2, 8, 500, 1).setDataValidation(rule);
  }
  if(!ss.getSheetByName(CONFIG.SHEET_LOG)){
    const lg = ss.insertSheet(CONFIG.SHEET_LOG);
    lg.getRange(1,1,1,4).setValues([["시각","종류","학교ID","내용"]]).setFontWeight("bold");
    lg.setFrozenRows(1);
  }
  const first = ss.getSheets()[0];
  if(first.getName()==="시트1" || first.getName()==="Sheet1") { if(ss.getSheets().length>1) ss.deleteSheet(first); }
  SpreadsheetApp.getUi().alert("준비됐어요. 이제 [배포 → 새 배포 → 웹 앱]으로 배포한 뒤, 메뉴 [3. 웹 앱 URL 확인]으로 주소를 확인하세요.");
}

function showWebAppUrl(){
  const url = ScriptApp.getService().getUrl();
  SpreadsheetApp.getUi().alert(url ? "웹 앱 URL (사이트 schools.json의 operatorUrl에 넣으세요):\n\n"+url
                                   : "아직 배포되지 않았어요. [배포 → 새 배포 → 유형: 웹 앱 / 실행: 나 / 액세스: 모든 사용자]로 배포하세요.");
}

// ===================== 웹 앱 진입점 =====================
function doGet(e){
  const p = (e && e.parameter) || {};
  try{
    if(p.action==="status"){          // ?action=status&school=hyosung
      const row = findSchool_(p.school);
      return json_({ ok:true, school:p.school, collect: !!(row && row.status===STATUS.OK) });
    }
    if(p.action==="list"){            // 승인된 학교 ID 목록 (사이트가 한 번에 확인)
      return json_({ ok:true, collect: listSchools_().filter(r=>r.status===STATUS.OK).map(r=>r.id) });
    }
    return json_({ ok:true, service:"curriculum-fair-operator", version:1 });
  }catch(err){ return json_({ ok:false, error:String(err) }); }
}

function doPost(e){
  let body = {};
  try{ body = JSON.parse((e.postData && e.postData.contents) || "{}"); }catch(err){ return json_({ok:false,error:"bad json"}); }
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try{
    if(body.action==="register") return json_(register_(body));
    return json_(recordSubmission_(body));      // 기본: 학생 제출
  }catch(err){
    log_("오류", body.schoolId||"", String(err));
    return json_({ ok:false, error:String(err) });
  }finally{ lock.releaseLock(); }
}

// ===================== 신청 접수 =====================
function register_(b){
  const id = clean_(b.schoolId).replace(/[^a-z0-9_-]/gi,"").toLowerCase();
  const name = clean_(b.schoolName), email = clean_(b.email).toLowerCase();
  if(!id || !name) return { ok:false, error:"학교 정보가 없어요." };
  if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return { ok:false, error:"이메일 형식을 확인해 주세요." };

  const sh = schoolsSheet_();
  const existing = findSchool_(id);
  if(existing){
    // 이미 있는 학교: 대기/중지 상태면 담당자 정보만 갱신, 승인 상태면 그대로 안내
    if(existing.status===STATUS.OK) return { ok:true, already:true, message:"이미 승인된 학교예요. 담당 선생님 메일함의 시트 링크를 확인하세요." };
    sh.getRange(existing.row, 5, 1, 3).setValues([[clean_(b.teacher), email, clean_(b.phone)]]);
    sh.getRange(existing.row, 13).setValue(clean_(b.note));
    log_("재신청", id, name+" / "+email);
    return { ok:true, message:"신청이 접수됐어요. 승인되면 이메일로 시트 링크를 보내드려요." };
  }
  sh.appendRow([id, name, clean_(b.region), clean_(b.district), clean_(b.teacher), email, clean_(b.phone),
                STATUS.WAIT, "", new Date(), "", 0, clean_(b.note)]);
  log_("신청", id, name+" / "+email);
  notifyOperator_(`[신청] ${name} (${id})`, `담당: ${clean_(b.teacher)} <${email}>\n연락처: ${clean_(b.phone)}\n메모: ${clean_(b.note)}\n\n운영 시트에서 상태를 '승인'으로 바꾸고 [승인 처리 실행]을 누르세요.\n${SpreadsheetApp.getActiveSpreadsheet().getUrl()}`);
  return { ok:true, message:"신청이 접수됐어요. 승인되면 이메일로 시트 링크를 보내드려요." };
}

// ===================== 승인 처리 =====================
/** 상태가 '승인'인데 시트URL이 비어 있는 학교마다: 결과 시트 생성 → 담당자에게 공유 → 메일 */
function processApprovals(){
  const sh = schoolsSheet_();
  const rows = listSchools_();
  let done = 0;
  rows.forEach(r=>{
    if(r.status!==STATUS.OK || r.sheetUrl) return;
    const file = createSchoolSheet_(r);
    const links = schoolLinks_(r.id);
    const qr = makeQr_(r, links.lock);                      // {blob, fileUrl} 또는 null
    sh.getRange(r.row, 9).setValue(file.getUrl());
    sh.getRange(r.row, 11).setValue(new Date());
    sh.getRange(r.row, 14).setValue(links.short);
    if(qr) sh.getRange(r.row, 15).setValue(qr.fileUrl);
    addLinksToSheet_(file, r, links, qr);
    if(r.email){
      shareSheet_(file, r.email);
      sendApprovalMail_(r, file.getUrl(), links, qr);
    }
    log_("승인", r.id, r.name+" → "+file.getUrl());
    done++;
  });
  if(SpreadsheetApp.getActiveSpreadsheet() && typeof SpreadsheetApp.getUi === "function"){
    try{ SpreadsheetApp.getUi().alert(done ? `${done}개 학교 시트를 만들고 공유했어요.` : "처리할 학교가 없어요. (상태='승인' + 시트URL 비어 있음 조건)"); }catch(e){}
  }
  return done;
}

/** '학교' 탭에서 상태 칸을 바꿀 때 자동으로 승인 처리하고 싶으면 메뉴에서 한 번 켭니다. */
function installEditTrigger(){
  const has = ScriptApp.getProjectTriggers().some(t=>t.getHandlerFunction()==="onEditApprove_");
  if(!has) ScriptApp.newTrigger("onEditApprove_").forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet()).onEdit().create();
  SpreadsheetApp.getUi().alert("켜졌어요. 이제 '학교' 탭에서 상태를 '승인'으로 바꾸면 자동으로 시트가 만들어지고 메일이 갑니다.");
}
function onEditApprove_(e){
  try{
    const rng = e.range, sh = rng.getSheet();
    if(sh.getName()!==CONFIG.SHEET_SCHOOLS || rng.getColumn()!==8 || rng.getRow()<2) return;
    if(String(e.value)!==STATUS.OK) return;
    processApprovals();
  }catch(err){ log_("오류","",String(err)); }
}

function createSchoolSheet_(r){
  const folder = getFolder_();
  const title = `[${r.name}] 과목 선택 결과 — ${CONFIG.SITE_NAME}`;
  let file;
  if(CONFIG.TEMPLATE_SPREADSHEET_ID){
    file = DriveApp.getFileById(CONFIG.TEMPLATE_SPREADSHEET_ID).makeCopy(title, folder);
  }else{
    const ss = SpreadsheetApp.create(title);
    file = DriveApp.getFileById(ss.getId());
    folder.addFile(file); DriveApp.getRootFolder().removeFile(file);
    initResultSheet_(ss, r);
  }
  return file;
}

/** 기본 결과 시트 형식: '선택결과'(제출 1행씩, 과목별 1 체크) + '집계'(과목별·학년별 인원) + '안내' */
function initResultSheet_(ss, r){
  const res = ss.getSheets()[0]; res.setName("선택결과");
  const head = ["제출시각","학번","학년","반","번호","이름","선택과목"];
  res.getRange(1,1,1,head.length).setValues([head]).setFontWeight("bold").setBackground("#F2F4F9");
  res.setFrozenRows(1); res.setFrozenColumns(2);
  res.setColumnWidth(1,150); res.setColumnWidth(7,360);

  const agg = ss.insertSheet("집계");
  agg.getRange(1,1,1,5).setValues([["과목","전체","1학년","2학년","3학년"]]).setFontWeight("bold").setBackground("#F2F4F9");
  agg.setFrozenRows(1);
  agg.getRange("A2").setValue("(학생이 제출하면 과목이 자동으로 추가돼요)");

  const info = ss.insertSheet("안내");
  info.getRange(1,1,8,1).setValues([[`${r.name} 과목 선택 결과 시트`],[""],
    ["· '선택결과' 탭: 학생이 제출할 때마다 한 줄씩 쌓입니다. 같은 학번이 다시 제출하면 그 줄이 갱신됩니다."],
    ["· H열부터는 과목별로 1이 표시됩니다(선택함). 처음 등장하는 과목은 자동으로 열이 추가됩니다."],
    ["· '집계' 탭: 과목별·학년별 선택 인원이 수식으로 계산됩니다. 정렬·필터는 자유롭게 하세요."],
    ["· 이 시트의 열 이름(1행)은 바꾸지 마세요. 접수 스크립트가 열 이름으로 기록합니다."],
    [`· 사이트: ${CONFIG.SITE_URL}?school=${r.id}#checklist`],
    [`· 문의: ${CONFIG.OPERATOR_NAME}`]]);
  info.getRange("A1").setFontWeight("bold").setFontSize(14);
  info.setColumnWidth(1, 720);
}

function shareSheet_(file, email){
  try{
    file.addEditor(email);
    if(CONFIG.TRANSFER_OWNERSHIP){ try{ file.setOwner(email); }catch(e){ log_("소유권이전실패","",String(e)); } }
  }catch(e){ log_("공유실패","",email+" "+e); }
}

/** 학교 전용 주소: lock = 잠금 링크(학교 전환 불가), short = 짧은 폴더 주소(저장소에 <id>/index.html 이 있을 때 동작) */
function schoolLinks_(id){
  const base = CONFIG.SITE_URL.replace(/\/+$/,"") + "/";
  return { lock: base + "?school=" + encodeURIComponent(id) + "&lock=1", short: base + encodeURIComponent(id) + "/" , student: base + "?school=" + encodeURIComponent(id) + "&lock=1#checklist" };
}
/** QR 이미지(PNG) 생성 → 학교 폴더에 저장. 실패하면 null (메일은 주소만으로 발송) */
function makeQr_(r, link){
  try{
    const api = "https://api.qrserver.com/v1/create-qr-code/?size=700x700&margin=12&format=png&data=" + encodeURIComponent(link);
    const res = UrlFetchApp.fetch(api, { muteHttpExceptions:true });
    if(res.getResponseCode()!==200) throw new Error("QR API "+res.getResponseCode());
    const blob = res.getBlob().setName(`[${r.name}] 교육과정박람회 QR.png`);
    const folder = getFolder_();
    const f = folder.createFile(blob);
    f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    return { blob, fileUrl: f.getUrl(), fileId: f.getId() };
  }catch(e){ log_("QR실패", r.id, String(e)); return null; }
}
/** 학교 결과 시트 '안내' 탭에 전용 주소와 QR 삽입 */
function addLinksToSheet_(file, r, links, qr){
  try{
    const ss = SpreadsheetApp.openById(file.getId());
    const info = ss.getSheetByName("안내"); if(!info) return;
    const row = info.getLastRow() + 2;
    info.getRange(row,1,4,1).setValues([["▶ 학생 배포용 학교 전용 주소 (이 주소로만 안내하세요 — 다른 학교로 바뀌지 않도록 잠겨 있습니다)"],[links.short],[links.lock],["   QR 이미지는 아래에 있고, 드라이브 파일: " + (qr ? qr.fileUrl : "(생성 실패)")]]);
    info.getRange(row,1).setFontWeight("bold");
    if(qr) info.insertImage(qr.blob, 1, row+5).setWidth(220).setHeight(220);
  }catch(e){ log_("안내탭실패", r.id, String(e)); }
}

function sendApprovalMail_(r, url, links, qr){
  links = links || schoolLinks_(r.id);
  const subject = `[${CONFIG.SITE_NAME}] ${r.name} 결과 수집이 승인됐어요 — 결과 시트 · 학생 배포용 주소 · QR`;
  const text =
`${r.teacher||"선생님"}께,

${r.name}의 과목 선택 결과 수집이 승인되었습니다.

▶ 결과 시트 (편집자 권한으로 공유됨)
${url}

▶ 학생에게 배포할 학교 전용 주소 (이 주소만 안내하세요)
${links.short}
(같은 주소) ${links.lock}
※ 이 주소로 접속하면 ${r.name} 페이지로 고정되어 다른 학교로 바뀌지 않고, 제출도 이 학교 시트로만 들어갑니다.
※ QR 이미지가 첨부되어 있습니다. 가정통신문·게시판에 그대로 쓰세요.

시트의 '안내' 탭에 사용법과 같은 주소·QR이 들어 있습니다. 궁금한 점은 이 메일로 회신해 주세요.

${CONFIG.OPERATOR_NAME} 드림`;
  const html =
`<div style="font-family:Apple SD Gothic Neo,Malgun Gothic,sans-serif;font-size:15px;line-height:1.7;color:#1f2b4d;max-width:640px">
<p>${esc_(r.teacher||"선생님")}께,</p>
<p><b>${esc_(r.name)}</b>의 과목 선택 결과 수집이 승인되었습니다.</p>
<h3 style="margin:22px 0 6px">📄 결과 시트</h3>
<p><a href="${url}">${url}</a><br><span style="color:#667">편집자 권한으로 공유되었습니다. 학생이 제출하면 실시간으로 쌓입니다.</span></p>
<h3 style="margin:22px 0 6px">🔗 학생에게 배포할 학교 전용 주소</h3>
<p style="font-size:18px"><a href="${links.short}"><b>${links.short}</b></a></p>
<p style="color:#667;font-size:13px">같은 주소: <a href="${links.lock}">${links.lock}</a><br>이 주소로 접속하면 <b>${esc_(r.name)}</b> 페이지로 고정되어 다른 학교로 바뀌지 않고, 제출도 이 학교 시트로만 들어갑니다.</p>
${qr ? `<h3 style="margin:22px 0 6px">📱 QR 코드</h3><p><img src="cid:qr" width="220" height="220" style="border:1px solid #ddd;border-radius:12px"><br><span style="color:#667;font-size:13px">첨부 파일로도 들어 있습니다. 가정통신문·학급 게시판에 그대로 쓰세요.</span></p>` : ""}
<p style="margin-top:22px;color:#667;font-size:13px">시트의 '안내' 탭에 사용법과 같은 주소·QR이 들어 있습니다. 궁금한 점은 이 메일로 회신해 주세요.</p>
<p>${esc_(CONFIG.OPERATOR_NAME)} 드림</p></div>`;
  const opt = { to:r.email, subject, body:text, htmlBody:html, name:CONFIG.OPERATOR_NAME };
  if(qr){ opt.inlineImages = { qr: qr.blob }; opt.attachments = [qr.blob]; }
  MailApp.sendEmail(opt);
}
function esc_(s){ return String(s==null?"":s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

/** 메뉴용: 선택한 행(또는 승인된 모든 학교)의 안내 메일을 다시 보냄 (주소·QR 포함) */
function resendApprovalMail(){
  const sh = schoolsSheet_(); const ui = SpreadsheetApp.getUi();
  const row = sh.getActiveRange() ? sh.getActiveRange().getRow() : 0;
  const rows = listSchools_().filter(r=> r.status===STATUS.OK && r.sheetUrl && (row<2 || r.row===row));
  if(!rows.length){ ui.alert("보낼 대상이 없어요. '학교' 탭에서 승인된 학교의 행을 선택한 뒤 실행하세요."); return; }
  rows.forEach(r=>{
    const links = schoolLinks_(r.id);
    let qr=null;
    try{ if(r.qrUrl){ const id=r.qrUrl.match(/[-\w]{25,}/)[0]; const f=DriveApp.getFileById(id); qr={blob:f.getBlob(), fileUrl:f.getUrl()}; } }catch(e){}
    if(!qr) qr = makeQr_(r, links.lock);
    if(qr && !r.qrUrl) sh.getRange(r.row,15).setValue(qr.fileUrl);
    if(!r.link) sh.getRange(r.row,14).setValue(links.short);
    if(r.email) sendApprovalMail_(r, r.sheetUrl, links, qr);
    log_("재발송", r.id, r.email);
  });
  ui.alert(`${rows.length}개 학교에 안내 메일을 다시 보냈어요.`);
}

// ===================== 학생 제출 기록 =====================
function recordSubmission_(b){
  let ss;
  if(b.sheetId){
    // 기존 '방법 A'(학교 시트에 운영자 계정이 편집자로 추가된 경우) 그대로 지원
    ss = SpreadsheetApp.openById(String(b.sheetId));
  }else{
    const id = clean_(b.schoolId);
    const r = findSchool_(id);
    if(!r) return { ok:false, error:"등록되지 않은 학교예요." };
    if(r.status!==STATUS.OK || !r.sheetUrl) return { ok:false, error:"아직 결과 수집이 승인되지 않은 학교예요." };
    ss = SpreadsheetApp.openByUrl(r.sheetUrl);
    schoolsSheet_().getRange(r.row, 12).setValue((+r.count||0)+1);
  }
  const res = ss.getSheetByName("선택결과") || ss.getSheets()[0];
  writeRow_(res, b);
  updateAgg_(ss, res);
  return { ok:true };
}

function writeRow_(sh, b){
  const selected = Array.isArray(b.selected) ? b.selected.map(clean_).filter(Boolean) : [];
  const FIXED = 7;   // 제출시각~선택과목
  // 1행 헤더 읽기, 없으면 만들기
  let lastCol = Math.max(sh.getLastColumn(), FIXED);
  if(sh.getLastRow()===0){
    sh.getRange(1,1,1,FIXED).setValues([["제출시각","학번","학년","반","번호","이름","선택과목"]]).setFontWeight("bold").setBackground("#F2F4F9");
    sh.setFrozenRows(1);
  }
  let header = sh.getRange(1,1,1,lastCol).getValues()[0].map(v=>String(v||""));
  // 새 과목 열 추가
  const missing = selected.filter(s=>header.indexOf(s)<0);
  if(missing.length){
    sh.getRange(1, header.length+1, 1, missing.length).setValues([missing]).setFontWeight("bold").setBackground("#F2F4F9");
    header = header.concat(missing);
  }
  const row = new Array(header.length).fill("");
  row[0]=new Date(); row[1]=clean_(b.studentId); row[2]=clean_(b.grade); row[3]=clean_(b.classNo);
  row[4]=clean_(b.number); row[5]=clean_(b.name); row[6]=selected.join(", ");
  selected.forEach(s=>{ const c=header.indexOf(s); if(c>=0) row[c]=1; });
  // 같은 학번이 이미 있으면 그 줄을 갱신
  let target = 0;
  if(row[1]){
    const ids = sh.getLastRow()>1 ? sh.getRange(2,2,sh.getLastRow()-1,1).getValues().map(v=>String(v[0])) : [];
    const idx = ids.indexOf(String(row[1]));
    if(idx>=0) target = idx+2;
  }
  if(target){ sh.getRange(target,1,1,row.length).clearContent(); sh.getRange(target,1,1,row.length).setValues([row]); }
  else sh.appendRow(row);
}

/** '집계' 탭을 헤더 기준으로 다시 씁니다 (과목별 전체/학년별 인원). */
function updateAgg_(ss, res){
  const agg = ss.getSheetByName("집계"); if(!agg) return;
  const lastCol = res.getLastColumn(); if(lastCol<=7) return;
  const header = res.getRange(1,8,1,lastCol-7).getValues()[0];
  const rows = header.map((name,i)=>{
    const col = colLetter_(8+i);
    return [name,
      `=COUNTIF('선택결과'!${col}:${col},1)`,
      `=COUNTIFS('선택결과'!$C:$C,"1",'선택결과'!${col}:${col},1)+COUNTIFS('선택결과'!$C:$C,1,'선택결과'!${col}:${col},1)`,
      `=COUNTIFS('선택결과'!$C:$C,"2",'선택결과'!${col}:${col},1)+COUNTIFS('선택결과'!$C:$C,2,'선택결과'!${col}:${col},1)`,
      `=COUNTIFS('선택결과'!$C:$C,"3",'선택결과'!${col}:${col},1)+COUNTIFS('선택결과'!$C:$C,3,'선택결과'!${col}:${col},1)`];
  });
  agg.getRange(2,1,Math.max(agg.getLastRow()-1,1),5).clearContent();
  agg.getRange(2,1,rows.length,5).setValues(rows);
}

// ===================== 유틸 =====================
function schoolsSheet_(){
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(CONFIG.SHEET_SCHOOLS);
  if(!sh) throw new Error("'학교' 탭이 없어요. 메뉴 [1. 초기 설정]을 먼저 실행하세요.");
  return sh;
}
function listSchools_(){
  const sh = schoolsSheet_(); const n = sh.getLastRow(); if(n<2) return [];
  return sh.getRange(2,1,n-1,SCHOOL_COLS.length).getValues().map((v,i)=>({
    row:i+2, id:String(v[0]).trim(), name:v[1], region:v[2], district:v[3], teacher:v[4], email:String(v[5]).trim(),
    phone:v[6], status:String(v[7]).trim(), sheetUrl:String(v[8]).trim(), requestedAt:v[9], approvedAt:v[10], count:v[11], note:v[12],
    link:String(v[13]||"").trim(), qrUrl:String(v[14]||"").trim()
  })).filter(r=>r.id);
}
function findSchool_(id){ id=String(id||"").trim().toLowerCase(); if(!id) return null; return listSchools_().find(r=>r.id.toLowerCase()===id) || null; }
function refreshCounts(){
  const sh = schoolsSheet_();
  listSchools_().forEach(r=>{
    if(!r.sheetUrl) return;
    try{ const s=SpreadsheetApp.openByUrl(r.sheetUrl).getSheetByName("선택결과"); if(s) sh.getRange(r.row,12).setValue(Math.max(s.getLastRow()-1,0)); }catch(e){}
  });
}
function getFolder_(){
  const it = DriveApp.getFoldersByName(CONFIG.RESULT_FOLDER_NAME);
  return it.hasNext() ? it.next() : DriveApp.createFolder(CONFIG.RESULT_FOLDER_NAME);
}
function notifyOperator_(subject, body){
  try{ MailApp.sendEmail({ to: Session.getEffectiveUser().getEmail(), subject:`[박람회 운영] ${subject}`, body }); }catch(e){}
}
function log_(kind, id, text){
  try{ const lg=SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SHEET_LOG); if(lg) lg.appendRow([new Date(), kind, id, text]); }catch(e){}
}
function clean_(v){ return v==null ? "" : String(v).replace(/[\r\n\t]/g," ").trim().slice(0,500); }
function colLetter_(n){ let s=""; while(n>0){ const m=(n-1)%26; s=String.fromCharCode(65+m)+s; n=Math.floor((n-1)/26); } return s; }
function json_(obj){ return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }

// ===================== 테스트 (편집기에서 직접 실행) =====================
function test_registerAndSubmit(){
  Logger.log(register_({schoolId:"testschool", schoolName:"테스트고등학교", region:"인천", district:"계양구", teacher:"홍길동", email:Session.getEffectiveUser().getEmail(), phone:"", note:"테스트"}));
  const sh=schoolsSheet_(); const r=findSchool_("testschool"); sh.getRange(r.row,8).setValue(STATUS.OK);
  processApprovals();
  Logger.log(recordSubmission_({schoolId:"testschool", studentId:"10101", grade:"1", classNo:"1", number:"1", name:"테스트", selected:["물리학","화학","세계사"]}));
  Logger.log(recordSubmission_({schoolId:"testschool", studentId:"10101", grade:"1", classNo:"1", number:"1", name:"테스트", selected:["물리학","생명과학"]}));
}
