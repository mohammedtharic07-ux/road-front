// If the frontend is served from the static dev server (port 8000),
// call the backend at port 5000. Otherwise use the current origin
// so serving via Flask (same origin) works transparently.
const API = (location.port === '8000') ? 'http://127.0.0.1:5000' : location.origin;

console.log("🚀 Login page loaded. API URL:", API);

async function sendOtp() {
  const name = document.getElementById("name").value.trim();
  const number = document.getElementById("number").value.trim();
  const statusMsg = document.getElementById("statusMsg");

  if(!name || !number){
    alert("Enter name and phone number");
    return;
  }

  console.log("📤 Sending OTP for:", name, number);

  try{
    const res = await fetch(`${API}/send-otp`,{
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      credentials:"include",
      body: JSON.stringify({ name, number })
    });
    
    console.log("📨 Response status:", res.status);
    const data = await res.json();
    console.log("📨 Response data:", data);

    if(res.ok){
      statusMsg.style.color = "green";
      let message = " OTP sent successfully! ";

      // Frontend will not show OTP, terminal will display
      message += "Check Flask terminal for the OTP code.";

      statusMsg.innerHTML = message;

      // Show OTP input section
      document.getElementById("otpSection").style.display = "block";
      document.getElementById("sendOtpBtn").disabled = true;

      // Save number for verify
      document.getElementById("otpSection").dataset.number = number;

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
  const number = document.getElementById("otpSection").dataset.number;
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
      body: JSON.stringify({ number, otp })
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