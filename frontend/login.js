// Local development backend URL. In production, set window.BACKEND_URL to your Render backend URL.
const LOCAL_API_URL = 'http://127.0.0.1:5000';
const API = window.BACKEND_URL || LOCAL_API_URL;

console.log("🚀 Login page loaded. API URL:", API);

async function sendOtp() {
  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const statusMsg = document.getElementById("statusMsg");

  if(!name || !email){
    alert("Enter name and email");
    return;
  }

  console.log("📤 Sending OTP for:", name, email);

  try{
    const res = await fetch(`${API}/send-otp`,{
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      credentials:"include",
      body: JSON.stringify({ name, email })
    });
    
    console.log("📨 Response status:", res.status);
    const data = await res.json();
    console.log("📨 Response data:", data);

    if(res.ok){
      statusMsg.style.color = "green";
      let message = "OTP sent successfully. Check your email inbox.";

      statusMsg.innerHTML = message;

      // Show OTP input section
      document.getElementById("otpSection").style.display = "block";
      document.getElementById("sendOtpBtn").disabled = true;

      // Save email for verify
      document.getElementById("otpSection").dataset.email = email;

    }else{
      statusMsg.style.color = "red";
      statusMsg.innerText = "❌ " + (data.error || "Failed to send OTP");
      console.error("OTP send failed:", data);
    }

  }catch(err){
    console.error("❌ Fetch error:", err);
    statusMsg.style.color = "red";
    statusMsg.innerText = `❌ Network error: ${err.message}. Make sure backend is running at ${API}`;
  }
}

async function verifyOtp(){
  const email = document.getElementById("otpSection").dataset.email;
  const otp = document.getElementById("otpInput").value.trim();
  const statusMsg = document.getElementById("statusMsg");

  if(!otp){
    alert("Enter OTP");
    return;
  }

  try{
    const res = await fetch(`${API}/verify-otp`,{
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      credentials:"include",
      body: JSON.stringify({ email, otp })
    });

    const data = await res.json();

    if(res.ok){
      statusMsg.style.color = "green";
      statusMsg.innerText = " Login successful. Redirecting...";
      // Redirect to dashboard on the same origin to avoid cross-origin path issues
      setTimeout(() => {
        window.location.href = `${location.origin}/index.html`;
      }, 1000);
    } else {
      statusMsg.style.color = "red";
      statusMsg.innerText = data.error || "OTP verification failed";
    }

  }catch(err){
    console.error(err);
    statusMsg.style.color = "red";
    statusMsg.innerText = "Network error. Try again.";
  }
}