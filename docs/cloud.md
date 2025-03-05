# Running MESSAGE on Arbutus

This guide provides step-by-step instructions for **setting up and running MESSAGEix-Canada on Arbutus**.  
Additionally, it includes a section on **setting up the model on a cloud environment** for scalability.

## Prerequisites (One-Time Setup)

### Step 1: Download and Install MobaXterm
1. Open your web browser and go to [MobaXterm's official website](https://mobaxterm.mobatek.net/download.html).
2. Download and install the latest version of MobaXterm.

### Step 2: Generate an SSH Key Pair
1. Open **MobaXterm**.
2. Click on **Tools** in the top menu bar.
3. Select **MobaKeyGen (SSH key generator)**.
4. Click **Generate** and move your mouse randomly inside the window until the progress bar completes.
5. Once generated:
   - Click **Save private key** → Choose a secure location.
   - Click **Save public key** → Save it in the same location.
6. Copy the public key from the text box and send it to **Bipasa Agrawal (bipasaagrawal@uvic.ca)** to enable SSH access.
7. Check your IP address at [whatismyipaddress.com](https://whatismyipaddress.com/) and send your **IPv4 address** to Bipasa to gain access to the Arbutus cloud instance.

### Step 3: Connect to the Remote Server via SSH
1. Open **MobaXterm**.
2. Click **Session** → Select **SSH**.
3. In the **Remote Host** field, enter:
   ```plaintext
   206.12.95.240
   ```
4. Check **Specify username** and enter your provided username.
5. Click **Advanced SSH settings**.
6. Under **Use private key**, click **Browse** and select the private key you generated earlier.
7. Click **OK** to start the SSH session.
8. If prompted with a security warning, select **Yes**.
9. You are now connected to the server.

---

## Setting Up the `messageix-canada` Repository and Job Scheduler

### 1. Accessing the SHARED Folder
Once connected to the instance:
```bash
cd ..
cd SHARED
```
Create a new folder inside `SHARED` (use a meaningful name, e.g., with your username):
```bash
mkdir message_bipasa
```
📌 The **SHARED** folder is accessible by all users with SSH access to this instance.

### 2. Cloning the Repository
Inside your newly created folder:
```bash
cd message_bipasa
git clone https://gitlab.com/sesit/message-ix.git
cd message-ix
git checkout dev  # Switch to the dev branch
```
To pull the latest changes from the `dev` branch:
```bash
git pull origin dev
```
Alternatively, instead of cloning, you can upload your local `messageix-canada` repository into this folder.
📌 **CAUTION:** Store all model folders/repos inside `SHARED`, **not** in your personal folder.

### 3. Setting Up Your Personal Directory
Move **one level up** from the `SHARED` folder:
```bash
cd ..
```
Navigate to your personal folder and create a `.kube` directory:
```bash
mkdir .kube
cd .kube
```
Upload the **config** file here. *(Message Bipasa if you don't have this file.)*

Go back to your personal folder and create a directory for job scheduling:
```bash
cd ..
mkdir job_scheduler
cd job_scheduler
```
Upload `create_message_job.py` into this folder. *(Message Bipasa if you don't have this file.)*

### 4. You're Ready!
You can now start running MESSAGE jobs as needed.

---

## Running a MESSAGE Job
To execute a MESSAGE job, use the following command format (remember to change the folder names):
```bash
python3 "/home/bipasa25/job_scheduler/create_message_job.py" \
        "/home/SHARED/message-bipasa" \
        "python3 MESSAGE_CA.py" "1"
```
📌 **Parameters:**
- **Path to** `create_message_job.py` (inside your user space)
- **Path to** `message-bipasa` (inside SHARED folder)
- **Command to run** the MESSAGE model (`MESSAGE_CA.py`)
- **Job number** (must be unique unless the previous job and its persistent volume are deleted)

To check job progress in logs:
```bash
kubectl logs <pod-name>
```

---

## Troubleshooting & Checking Status

### Checking Job Status
- Get a list of all jobs:
  ```
  kubectl get jobs
  ```
- Check if a job has completed or is still running.

### Deleting a Job
- Delete a specific job:
  ```
  kubectl delete job <job-name>
  ```

### Checking Pods
- List all pods:
  ```
  kubectl get pods
  ```
  *(Each job runs in a specific pod. If a job fails, multiple pods may be created for it.)*

- View logs of a specific pod:
  ```
  kubectl logs <pod-name>
  ```
  *(Useful for checking where the model stopped running.)*

### Managing Persistent Volumes
- Get a list of persistent volumes (PV):
  ```
  kubectl get pv
  ```
- Delete a specific PV:
  ```
  kubectl delete pv <pv-name>
  ```
- Get a list of persistent volume claims (PVC):
  ```
  kubectl get pvc
  ```
- Delete a specific PVC:
  ```
  kubectl delete pvc <pvc-name>
  ```

📌 **After completing the job and verifying results in** `message-ix`, **delete the job, PV, and PVC associated with it.**

### Checking if a Job Completed Successfully
Check logs to confirm successful job execution:
```
kubectl logs <pod-name>
