# KVM Cloud Auto-Scaler ☁️

## Overview
This project is a custom **Infrastructure-as-Code (IaC)** solution that implements **Elasticity** for local virtual machines. 

It mimics the behavior of **AWS Auto Scaling Groups** or **Kubernetes HPA** by monitoring the CPU load of a cluster and dynamically provisioning (cloning) or terminating (destroying) KVM instances in real-time.

## 🏗 Architecture
* **Hypervisor:** KVM (Kernel-based Virtual Machine) with QEMU/Libvirt.
* **Orchestrator:** Python script interacting with `virsh` CLI.
* **Scaling Logic:** Horizontal Scaling (Scale Out / Scale In).
* **Algorithm:** * **Scale Up:** Triggered when Cluster Average CPU > 80%.
    * **Scale Down:** Triggered when Cluster Average CPU < 20%.
    * **Stability:** Implements a "Cool-down Period" (60s) to prevent Boot Storm loops.

## 🚀 How It Works
1.  **Monitor:** The script continuously polls CPU metrics (`virsh domstats`) from all active nodes.
2.  **Decision:** It calculates the weighted average load of the cluster.
3.  **Action:**
    * **High Load:** It clones a "Golden Image" (Template VM) to create a new worker (`dynamic-worker-x`).
    * **Low Load:** It gracefully terminates and deletes the newest worker node (LIFO strategy).

## 🛠 Prerequisites
* Linux (Ubuntu/Fedora)
* KVM/QEMU installed (`sudo apt install qemu-kvm libvirt-daemon-system`)
* Python 3

## 🔧 Usage
```bash
sudo python3 autoscaler.py