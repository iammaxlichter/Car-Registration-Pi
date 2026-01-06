import time
import sys
import platform
from pathlib import Path
from dotenv import dotenv_values

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

REGISTER_URL = "https://www.register2park.com/register"

CHROME_BINARY_PI = "/usr/bin/chromium"
CHROMEDRIVER_PATH_PI = "/usr/bin/chromedriver"

# ---------- Helpers ----------

def wait_click(driver, selector, by=By.CSS_SELECTOR, timeout=20):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    try:
        el.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", el)
    return el


def wait_send(driver, selector, text, by=By.CSS_SELECTOR, timeout=20):
    # clickable > visible to avoid "element not interactable"
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)

    try:
        el.click()
        el.clear()
        el.send_keys(text)
    except WebDriverException:
        # fallback: set value via JS + dispatch events
        driver.execute_script("arguments[0].value = arguments[1];", el, text)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", el
        )
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el
        )

    return el


# ---------- Flow steps ----------

def select_property(driver, name: str):
    wait_send(driver, 'input[type="text"]', name)
    wait_click(driver, "#confirmProperty")
    print("✔ Typed property name and clicked Next:", name)


def select_property_result(driver):
    wait_click(driver, "button.select-property")
    print("✔ Selected property")


def accept_guest_rules(driver):
    modal = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.ID, "visitor-rules-modal"))
    )
    btn = modal.find_element(By.CSS_SELECTOR, "button.btn.btn-primary")
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    print("✔ Accepted guest rules")


def choose_visitor_parking(driver):
    btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "registrationTypeVisitor"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    print("✔ Selected Visitor Parking")


def enter_guest_code(driver, code: str):
    wait_send(driver, "#guestCode", code)
    wait_click(driver, "#propertyGuestCode")
    print("✔ Guest code:", code)


def fill_vehicle_info(driver, make: str, model: str, plate: str):
    wait_send(driver, "#vehicleMake", make)
    wait_send(driver, "#vehicleModel", model)
    wait_send(driver, "#vehicleLicensePlate", plate)
    wait_send(driver, "#vehicleLicensePlateConfirm", plate)

    # small pause for any client-side validation
    time.sleep(0.5)

    try:
        btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "vehicleInformationVIP"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        driver.execute_script("arguments[0].click();", btn)
        print(f"✔ Vehicle info: {make} {model} {plate} (clicked Next)")
    except TimeoutException as e:
        print("⚠ Could not find the Next button (#vehicleInformationVIP):", e)
        time.sleep(15)
        raise


def send_email_confirmation(driver, email: str):
    """
    On the approval page, click 'E-Mail Confirmation',
    then fill email and click Send in the modal.
    """
    try:
        print("⏳ Waiting for E-Mail Confirmation button...")
        btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "email-confirmation"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)

        try:
            driver.execute_script("arguments[0].click();", btn)
        except WebDriverException:
            btn.click()

        print("✔ Clicked E-Mail Confirmation button")

    except TimeoutException as e:
        print("⚠ Could not find email-confirmation-btn:", e)
        time.sleep(15)
        return

    try:
        print("⏳ Waiting for email confirmation modal...")
        modal = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "email-confirmation-view"))
        )

        input_el = modal.find_element(By.ID, "emailConfirmationEmailView")
        input_el.clear()
        input_el.send_keys(email)

        send_btn = modal.find_element(By.CSS_SELECTOR, "button.btn.btn-success")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", send_btn)
        try:
            driver.execute_script("arguments[0].click();", send_btn)
        except WebDriverException:
            send_btn.click()

        print(f"✔ Email confirmation sent to {email}")

    except TimeoutException as e:
        print("⚠ Email confirmation modal did not appear:", e)
        time.sleep(15)


def build_driver() -> webdriver.Chrome:
    """Create a Chrome/Chromium driver that works on both PC and Raspberry Pi."""
    machine = platform.machine().lower()
    print("Detected machine:", machine)

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")

    # Raspberry Pi / ARM
    if any(arch in machine for arch in ("arm", "aarch64")):
        options.binary_location = CHROME_BINARY_PI
        options.add_argument("--headless=new")  # or "--headless" if needed
        return webdriver.Chrome(
            service=Service(CHROMEDRIVER_PATH_PI),
            options=options,
        )

    # Windows / normal PC (uses webdriver-manager)
    from webdriver_manager.chrome import ChromeDriverManager

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )


# ---------- Main ----------

def main(profile: str):
    profile_path = Path("env") / f"{profile}.env"
    vals = dotenv_values(profile_path)

    if not vals:
        raise SystemExit(f"Profile not found: {profile_path}")

    PROPERTY_NAME = vals["PROPERTY_NAME"]
    GUEST_CODE = vals["GUEST_CODE"]
    MAKE = vals["VEHICLE_MAKE"]
    MODEL = vals["VEHICLE_MODEL"]
    PLATE = vals["LICENSE_PLATE"]
    EMAIL = vals.get("EMAIL_ADDRESS", "iammaxlichter@gmail.com")

    print(f"=== Running profile: {profile.capitalize()} ===")

    driver = build_driver()
    driver.maximize_window()

    try:
        driver.get(REGISTER_URL)

        select_property(driver, PROPERTY_NAME)
        select_property_result(driver)
        accept_guest_rules(driver)
        choose_visitor_parking(driver)
        enter_guest_code(driver, GUEST_CODE)
        time.sleep(2.5)
        fill_vehicle_info(driver, MAKE, MODEL, PLATE)
        send_email_confirmation(driver, EMAIL)

        time.sleep(5)

    finally:
        driver.quit()


if __name__ == "__main__":
    profile = sys.argv[1] if len(sys.argv) > 1 else "tatiana"
    main(profile)
