// API URL selection: localhost for dev, Render backend for production
const API =
  location.hostname === 'localhost' ||
  location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:5000'
  : 'https://road-front.onrender.com';

let isAdmin = false;

/* ---------------- LOGIN CHECK ---------------- */
async function checkLogin(){
  const res = await fetch(`${API}/user-dashboard`,{ credentials:"include" });
  if(!res.ok){
    window.location.href="login.html";
  }
}

/* ---------------- ROLE CHECK ---------------- */
async function checkRole(){
  try{
    const res = await fetch(`${API}/admin-dashboard`,{ credentials:"include" });
    if(res.ok){
      isAdmin = true;
      console.log("Admin logged in");
    }
  }catch(err){
    console.log("Normal user");
  }
}

/* ---------------- INIT ---------------- */
async function init(){
  await checkLogin();
  await checkRole();
  await getRoads();
}
init();

/* ---------------- GET ROADS ---------------- */
async function getRoads(){
  const res = await fetch(`${API}/roads`,{ credentials:"include" });
  const data = await res.json();
  const list = document.getElementById("roadsList");
  list.innerHTML="";
  data.forEach(road=>{
    const li = document.createElement("li");
    li.innerHTML = `
      <b>${road.roadName}</b> - ${road.area} (${road.condition})<br>
      ID: ${road._id}
      <button onclick="copyId('${road._id}')">Copy</button>
      ${isAdmin ? `<button onclick="deleteRoad('${road._id}')">Delete</button>` : ""}
    `;
    list.appendChild(li);
  });
}

/* ---------------- COPY ROAD ID ---------------- */
function copyId(id){
  navigator.clipboard.writeText(id);
  alert("Road ID copied");
}

/* ---------------- ADD ROAD ---------------- */
async function addRoad(){
  const roadName = document.getElementById("roadName").value;
  const area = document.getElementById("area").value;
  const condition = document.getElementById("condition").value;
  if(!roadName || !area || !condition){
    alert("Fill all fields");
    return;
  }
  const res = await fetch(`${API}/add-road`,{
    method:"POST",
    credentials:"include",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({ roadName, area, condition })
  });
  const data = await res.json();
  alert(data.message || data.error);
  getRoads();
}

/* ---------------- DELETE ROAD ---------------- */
async function deleteRoad(id){
  if(!confirm("Delete this road?")) return;
  const res = await fetch(`${API}/delete-road/${id}`,{
    method:"DELETE",
    credentials:"include"
  });
  const data = await res.json();
  alert(data.message || data.error);
  getRoads();
}

/* ---------------- REPORT ISSUE ---------------- */
async function reportIssue(){
  const roadId = document.getElementById("roadId").value;
  const issueType = document.getElementById("issueType").value;
  const severity = document.getElementById("severity").value;
  const description = document.getElementById("desc").value;
  if(!roadId || !issueType || !severity || !description){
    alert("Fill all fields");
    return;
  }
  const res = await fetch(`${API}/report-issue`,{
    method:"POST",
    credentials:"include",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({ roadId, issueType, severity, description })
  });
  const data = await res.json();
  alert(data.message || data.error);
}

/* ---------------- AI DETECTION ---------------- */
async function uploadAndDetect(){
  const fileInput = document.getElementById("videoFile");
  const resultBox = document.getElementById("resultBox");
  if(!fileInput.files.length){
    alert("Select image/video");
    return;
  }

  // Show detecting
  resultBox.innerHTML = "Detecting... ⏳";

  // Disable detect button
  const detectBtn = document.querySelector(".btn-detect");
  detectBtn.disabled = true;

  const formData = new FormData();
  formData.append("file",fileInput.files[0]);

  console.log("🚀 Uploading file:", fileInput.files[0].name);
  console.log("📤 API URL:", API);

  try{
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 min timeout
    
    const res = await fetch(`${API}/detect-road-upload`,{
      method:"POST",
      credentials:"include",
      body:formData,
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    console.log("📊 Response status:", res.status);
    const data = await res.json();
    console.log("📊 Response data:", data);

    if(res.ok){
      // Show detections count
      let html=`<p>Detected issues: ${data.detections || 0}</p>`;
      
      // Show output image/video if available
      if(data.output_image){
        const imageSrc = data.output_image.startsWith('http') ? data.output_image : `${API}${data.output_image}`;
        console.log("🖼️  Image URL:", imageSrc);
        html+=`<img src="${imageSrc}" width="600" onerror="console.error('Image load failed')"/>`;
      }
      if(data.output_video){
        const videoSrc = data.output_video.startsWith('http') ? data.output_video : `${API}${data.output_video}`;
        console.log("🎬 Video URL:", videoSrc);
        html+=`<video width="600" controls>
                 <source src="${videoSrc}" type="video/mp4">
               </video>`;
      }

      resultBox.innerHTML = html;

      // Show bell with animation
      const bell = document.getElementById("notifyBell");
      bell.style.display="inline";
      bell.classList.add("ring");
      setTimeout(()=>bell.classList.remove("ring"),1500);

      // Clear file input
      fileInput.value = "";

    }else{
      resultBox.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
      console.error("❌ Detection failed:", data);
    }

  }catch(err){
    console.error("❌ Fetch error:", err);
    if (err.name === 'AbortError') {
      resultBox.innerHTML = `<p style="color:red;">❌ Detection timed out. Video too long?</p>`;
    } else {
      resultBox.innerHTML = `<p style="color:red;">❌ Detection failed: ${err.message}</p>`;
    }
  }finally{
    detectBtn.disabled = false;
  }
}

/* ---------------- CAMERA CAPTURE ---------------- */
let camStream=null;

async function openCamera(){
  try{
    camStream = await navigator.mediaDevices.getUserMedia({video:true});
    const video = document.getElementById("camera");
    video.srcObject = camStream;
    video.style.display="block";
    document.getElementById("captureBtn").style.display="inline-block";
    document.getElementById("detectStatus").innerText="📷 Camera opened";
  }catch(err){
    alert("Allow camera permission");
  }
}

async function capturePhoto(){
  const video = document.getElementById("camera");
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video,0,0);
  const blob = await new Promise(resolve => canvas.toBlob(resolve,"image/jpeg"));
  const file = new File([blob],"capture.jpg",{type:"image/jpeg"});

  const input=document.getElementById("videoFile");
  const dt=new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;

  camStream.getTracks().forEach(track=>track.stop());
  video.style.display="none";
  document.getElementById("captureBtn").style.display="none";

  uploadAndDetect();
}

/* ---------------- LOGOUT ---------------- */
async function logout(){
  const res = await fetch(`${API}/logout`,{ credentials:"include" });
  if(res.ok){
    window.location.href="login.html";
  }
}