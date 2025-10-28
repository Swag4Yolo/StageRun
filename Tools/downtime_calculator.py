#!/usr/bin/env python3
"""
Network Downtime Calculator
---------------------------
Compute how many packets and how much data are lost during downtime
on a high-speed link.
"""

def calculate_loss(link_gbps, mtu_bytes, downtime_seconds):
    # Convert link speed to bits per second
    bits_per_sec = link_gbps * 1e9
    bits_per_packet = mtu_bytes * 8
    
    # Packets per second
    pps = bits_per_sec / bits_per_packet
    total_packets = pps * downtime_seconds
    
    # Data lost in bytes and gigabytes
    total_bytes = total_packets * mtu_bytes
    total_gb = total_bytes / 1e9
    
    return total_packets, total_gb

def main():
    print("=== === === === === === === === === ===")
    print("=== Network Downtime Loss Estimator ===")
    while True:
        print("=== === === === === === === === === ===")
        link_gbps = float(input("Enter link speed (Gbps): "))
        mtu_bytes = int(input("Enter packet size (MTU in bytes): "))
        downtime_seconds = float(input("Enter downtime duration (seconds): "))
        
        total_packets, total_gb = calculate_loss(link_gbps, mtu_bytes, downtime_seconds)
        
        print(f"\nResults for {link_gbps} Gbps, {mtu_bytes} B MTU, {downtime_seconds}s downtime:")
        print(f"→ Packets lost: {total_packets/1e6:.2f} million")
        print(f"→ Data lost:    {total_gb:.2f} GB")
        print()

if __name__ == "__main__":
    main()
