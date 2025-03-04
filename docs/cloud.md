# 🚀 Running MESSAGE on Arbutus & Cloud Setup

This guide provides step-by-step instructions for **setting up and running MESSAGEix-Canada on Arbutus**.  
Additionally, it includes a section on **setting up the model on a cloud environment** for scalability.

---

## **1️⃣ Prerequisites (One-Time Setup)**

Follow these steps **once** to set up your environment.

### **📥 Step 1: Download and Install MobaXterm**
- Download **MobaXterm** from its official website:  
  🔗 [MobaXterm Download](https://mobaxterm.mobatek.net/download.html)
- Install the latest version on your system.

---

### **🔑 Step 2: Generate an SSH Key Pair**
1. Open **MobaXterm**.
2. Go to **Tools** → Select **MobaKeyGen (SSH key generator)**.
3. Click **Generate** and move your mouse randomly inside the window until the progress bar completes.
4. Once generated:
   - Click **Save private key** → Choose a **secure location**.
   - Click **Save public key** → Save it in the **same location**.
5. Copy the **public key** from the text box and send it to **Bipasa Agrawal** for SSH access.
6. Also, check your **IPv4 address** here:  
   🔗 [What is My IP](https://whatismyipaddress.com/)  
   Send this **IPv4 address** to **Bipasa** for firewall access.

---

### **🔗 Step 3: Connect to Arbutus via SSH**
1. Open **MobaXterm**.
2. Click **Session** → Select **SSH**.
3. In the **Remote Host** field, enter:  
   ```plaintext
   206.12.95.240
4. Check "Specify username" and enter the provided username.
5. Click Advanced SSH settings.
6. Under "Use private key", click Browse and select the private key generated earlier.
7. Click OK to start the SSH session.If prompted with a security warning, select Yes.

✅ You are now connected to the Arbutus server!

## **2 Setting Up the MESSAGEix-Canada Repository**

Once connected to the Arbutus instance, follow these steps.

📂 Step 1: Accessing the SHARED Folder
Navigate to the SHARED directory:

sh
Copy
Edit
cd ..
cd SHARED
Create a new folder inside SHARED (use an identifier like your username):

sh
Copy
Edit
mkdir message_bipasa
cd message_bipasa
⚠️ Important:

The SHARED folder is accessible by all users with SSH access.
Do not store personal files here.
🛠 Step 2: Cloning the Repository
Inside your new folder, clone the messageix-canada repository:

sh
Copy
Edit
git clone https://gitlab.com/sesit/message-ix.git
cd message-ix
Switch to the development branch:

sh
Copy
Edit
git checkout dev
To pull the latest updates:

sh
Copy
Edit
git pull origin dev
Alternatively, you can upload your local repository instead of cloning.

⚠️ Important:

Always store model folders or repositories inside the SHARED folder, not in your personal directory.
📁 Step 3: Setting Up Your Personal Directory
Move one directory up from the SHARED folder:

sh
Copy
Edit
cd ..
Navigate to your personal user folder (accessible only by you).

🔹 Create a directory for Kubernetes configuration:
sh
Copy
Edit
mkdir .kube
cd .kube
Upload the config file into .kube. (Message Bipasa if you don’t have this file yet)

🔹 Set up job scheduling:
Go back to your personal folder:
sh
Copy
Edit
cd ..
Create a job scheduler directory:
sh
Copy
Edit
mkdir job_scheduler
cd job_scheduler
Upload the create_message_job.py script into the job_scheduler folder.
(Message Bipasa if you don’t have this file yet)
✅ You are now ready to schedule MESSAGE jobs! 🎯