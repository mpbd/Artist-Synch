import os
import ctypes
import psutil

def list_mounted_drives():
    drives = []

    for part in psutil.disk_partitions(all=True):
        if part.device:
            drives.append(part.device)
    return drives

def location_is_mounted(loc):
    if not isinstance(loc, dict):
        return False

    loc_id = loc.get("id")
    loc_label = loc.get("label")
    loc_path = loc.get("path")

    if not loc_id or not loc_label or not loc_path:
        return False

    # Normalize stored path → extract drive root ("D:\\")
    loc_drive_root = os.path.splitdrive(loc_path)[0] + "\\"
    
    for m in mounted_drives:
        if not isinstance(m, dict):
            continue
            
        m_id = m.get("id")
        m_label = m.get("label")
        m_root  = m.get("path")

        # Normalize mounted path too
        if m_root:
            m_root = os.path.splitdrive(m_root)[0] + "\\"

        # Strict match of: id, label, and drive root
        if (
            m_id == loc_id and
            m_label == loc_label and
            m_root == loc_drive_root
        ):
            return True

    return False

def get_drive_info(path):
    # Extract drive root like "D:\\"
    drive = os.path.splitdrive(path)[0] + "\\"

    # --- Drive Label ---
    volume_name_buffer = ctypes.create_unicode_buffer(1024)
    fs_name_buffer = ctypes.create_unicode_buffer(1024)
    serial_number = ctypes.c_ulong()

    ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive),
        volume_name_buffer,
        ctypes.sizeof(volume_name_buffer),
        ctypes.byref(serial_number),
        None,
        None,
        fs_name_buffer,
        ctypes.sizeof(fs_name_buffer)
    )

    label = volume_name_buffer.value
    uuid_hex = hex(serial_number.value)[2:].upper()

    return {
        "id": uuid_hex,
        "label": label or "unknown",
        "path": drive
    }