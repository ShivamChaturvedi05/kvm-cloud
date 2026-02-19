import subprocess
import time
import re

# --- CONFIGURATION ---
MAIN_VM = "labvm1"          # The Manager / Main Node
TEMPLATE_VM = "vm-rest"     # The Template (Must be SHUTOFF)
BASE_NAME = "dynamic-worker-" # Prefix for new VMs

UP_THRESHOLD = 80.0       # Scale UP if Average CPU > 80%
DOWN_THRESHOLD = 20.0     # Scale DOWN if Average CPU < 20%
MAX_VMS = 3               # Safety Limit (Max 3 extra workers, for now obv)
CHECK_INTERVAL = 5        # Check every 5 seconds
BOOT_WAIT_TIME = 60       # Safe time to wait for a new VM to boot (prevents loops)

def get_cpu_usage(vm_name):
    """Calculates CPU usage % for a SINGLE VM"""
    try:
        cmd = f"virsh domstats {vm_name} --cpu-total"
        # Reading 1
        output1 = subprocess.check_output(cmd, shell=True).decode()
        cpu_time1 = int(re.search(r"cpu.time=(\d+)", output1).group(1))
        time1 = time.time()
        
        time.sleep(1) # Measure over 1 second
        
        # Reading 2
        output2 = subprocess.check_output(cmd, shell=True).decode()
        cpu_time2 = int(re.search(r"cpu.time=(\d+)", output2).group(1))
        time2 = time.time()

        # Calculation
        cpu_usage = (cpu_time2 - cpu_time1) / (time2 - time1) / 1000000000 * 100
        return cpu_usage
    except:
        return 0.0

def get_active_workers():
    """Returns a list of extra worker VMs (dynamic-worker-1, etc.)"""
    try:
        output = subprocess.check_output("virsh list --name", shell=True).decode()
        workers = [line.strip() for line in output.splitlines() if line.startswith(BASE_NAME)]
        workers.sort() # Sort to keep order (1, 2, 3...)
        return workers
    except:
        return []

def calculate_cluster_average(workers):
    """
    Calculates Average CPU of the Whole Group:
    (Main VM + Worker 1 + Worker 2...) / Total Count
    """
    total_cpu = 0
    vm_count = 0
    
    # 1. Get Main VM CPU
    main_cpu = get_cpu_usage(MAIN_VM)
    print(f"   -> {MAIN_VM}: {main_cpu:.1f}%")
    total_cpu += main_cpu
    vm_count += 1
    
    # 2. Get Each Worker CPU
    for worker in workers:
        w_cpu = get_cpu_usage(worker)
        print(f"   -> {worker}: {w_cpu:.1f}%")
        total_cpu += w_cpu
        vm_count += 1
        
    # 3. Calculate Average
    average = total_cpu / vm_count
    return average

def scale_up(current_workers):
    """Creates a new VM"""
    new_id = len(current_workers) + 1
    new_vm_name = f"{BASE_NAME}{new_id}"
    
    print(f"⚠️  AVG LOAD HIGH! Scaling UP... Creating {new_vm_name}")
    
    # Clone and Start
    cmd = f"virt-clone --original {TEMPLATE_VM} --name {new_vm_name} --auto-clone"
    subprocess.run(cmd, shell=True)
    subprocess.run(f"virsh start {new_vm_name}", shell=True)
    print(f"🚀 {new_vm_name} joined the cluster.")
    
    # --- IMPORTANT FIX: WAIT FOR BOOT ---
    print(f"⏳ Waiting {BOOT_WAIT_TIME}s for {new_vm_name} to finish booting...")
    time.sleep(BOOT_WAIT_TIME)
    print("✅ Boot complete. Resuming monitoring...")

def scale_down(current_workers):
    """Deletes the last created VM"""
    victim_vm = current_workers[-1]
    
    print(f"✅ AVG LOAD LOW. Scaling DOWN... Destroying {victim_vm}")
    
    subprocess.run(f"virsh destroy {victim_vm}", shell=True)
    subprocess.run(f"virsh undefine {victim_vm} --remove-all-storage", shell=True)
    print(f"🗑️  {victim_vm} removed.")

# --- MAIN LOOP ---
print("--- REAL CLOUD (AVG CPU) AUTO-SCALER STARTED ---")
print(f"Cluster: {MAIN_VM} + {BASE_NAME}*")
print(f"Target: Maintain Average CPU between {DOWN_THRESHOLD}% and {UP_THRESHOLD}%")

while True:
    try:
        # 1. Find who is alive
        workers = get_active_workers()
        
        # 2. Calculate the Group Average
        print(f"\nScanning Cluster ({len(workers) + 1} nodes)...")
        avg_cpu = calculate_cluster_average(workers)
        
        print(f"📊 CLUSTER AVERAGE: {avg_cpu:.2f}%")

        # 3. Make Decision
        if avg_cpu > UP_THRESHOLD and len(workers) < MAX_VMS:
            scale_up(workers)
            
        elif avg_cpu < DOWN_THRESHOLD and len(workers) > 0:
            scale_down(workers)
            
    except KeyboardInterrupt:
        print("\nStopping...")
        break
    except Exception as e:
        print(f"Error: {e}")
    
    # Wait before next check
    time.sleep(CHECK_INTERVAL)