
import RPi.GPIO as GPIO
import time

# Define GPIO pins for Lane A and Lane B
LANE_A_PINS = {
    'red': 17,
    'yellow': 27,
    'green': 22
}
LANE_B_PINS = {
    'red': 23,
    'yellow': 24,
    'green': 25
}

# Initialize GPIO
def setup_gpio():
    """Configure GPIO pins as outputs for traffic lights."""
    GPIO.setmode(GPIO.BCM)
    for pin in LANE_A_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    for pin in LANE_B_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

# Control traffic lights for a single lane
def set_traffic_lights(lane_a_state, lane_b_state, duration):
    """Set LED states for Lane A and Lane B based on state (R, Y, G) and duration."""
    # Validate states
    valid_states = {'R', 'Y', 'G'}
    if lane_a_state not in valid_states or lane_b_state not in valid_states:
        raise ValueError("Invalid state. Use 'R', 'Y', or 'G'.")

    # Turn off all LEDs
    GPIO.output([17, 27, 22, 23, 24, 25], GPIO.LOW)

    # Set Lane A
    if lane_a_state == 'G':
        GPIO.output(LANE_A_PINS['green'], GPIO.HIGH)
    elif lane_a_state == 'Y':
        GPIO.output(LANE_A_PINS['yellow'], GPIO.HIGH)
    elif lane_a_state == 'R':
        GPIO.output(LANE_A_PINS['red'], GPIO.HIGH)

    # Set Lane B
    if lane_b_state == 'G':
        GPIO.output(LANE_B_PINS['green'], GPIO.HIGH)
    elif lane_a_state == 'Y':
        GPIO.output(LANE_B_PINS['yellow'], GPIO.HIGH)
    elif lane_a_state == 'R':
        GPIO.output(LANE_B_PINS['red'], GPIO.HIGH)

    time.sleep(duration)

# Control traffic light cycle based on car counts
def control_traffic_lights(lane_a_cars, lane_b_cars):
    """Adjust green light durations based on car counts for Lane A and Lane B."""
    base_green_time = 10  # Base green light duration (seconds)
    yellow_time = 3       # Yellow light duration
    min_green_time = 5    # Minimum green time
    max_green_time = 20   # Maximum green time

    total_cars = lane_a_cars + lane_b_cars
    if total_cars == 0:
        green_a_time = green_b_time = base_green_time
    else:
        # Proportionally allocate green time based on car counts
        green_a_time = min(max(min_green_time, base_green_time + (lane_a_cars / total_cars) * (max_green_time - base_green_time)), max_green_time)
        green_b_time = min(max(min_green_time, base_green_time + (lane_b_cars / total_cars) * (max_green_time - base_green_time)), max_green_time)

    print(f"Lane A: {lane_a_cars} cars, Green for {green_a_time:.1f}s | Lane B: {lane_b_cars} cars, Green for {green_b_time:.1f}s")
    # Lane A green, Lane B red
    set_traffic_lights('G', 'R', green_a_time)
    # Lane A yellow, Lane B red
    set_traffic_lights('Y', 'R', yellow_time)
    # Lane A red, Lane B green
    set_traffic_lights('R', 'G', green_b_time)
    # Lane A red, Lane B yellow
    set_traffic_lights('R', 'Y', yellow_time)

# Cleanup GPIO on exit
def cleanup():
    """Reset all GPIO pins to a safe state."""
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        setup_gpio()
        # Example usage with dummy car counts
        control_traffic_lights(3, 2)
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"Error: {e}")
        cleanup()
