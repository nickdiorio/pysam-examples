# https://nrel-pysam.readthedocs.io/en/latest/
# https://nrel-pysam.readthedocs.io/en/latest/#importing-a-sam-gui-case
# https://nrel-pysam.readthedocs.io/en/latest/Models.html

import json
import os
import PySAM.Pvwattsv5 as pvwatts
import PySAM.StandAloneBattery as battery
import PySAM.Utilityrate5 as utility
import PySAM.CashloanModel as cashloan
from PySAM.PySSC import *

ssc = PySSC()

# I generated json files using "Generate Code" option in example.sam in pysam-examples and exporting as json.
# Battery data is captured through detailed PV model, but will be used with PVWatts here
with open(os.path.join('pysam_inputs', "pvwatts.json")) as f:
    dic = json.load(f)
    pvwatts_dat = dict_to_ssc_table(dic, "pvwattsv5")
    pv = pvwatts.wrap(pvwatts_dat)

with open(os.path.join('pysam_inputs', "pvsamv1.json")) as f:
    dic = json.load(f)
    batt_dat = dict_to_ssc_table(dic, "battery")
    batt = battery.wrap(batt_dat)
    utility_dat = dict_to_ssc_table(dic, "utilityrate5")
    utilityrate = utility.wrap(utility_dat)
    loan_dat = dict_to_ssc_table(dic, "cashloan")
    loan = cashloan.wrap(loan_dat)


# run PV model
pv.execute()
ac = pv.Outputs.ac # W
gen = [i/1000 for i in ac]

# run Battery model
batt.System.gen = gen

# because version of PySAM is a little behind the development version I exported json from
batt.Battery.batt_power_discharge_max = 5.06
batt.Battery.batt_power_charge_max = 5.06

# possible dispatch options
#batt.Battery.batt_dispatch_choice = 0 # perfect forecast peak shaving
#batt.Battery.batt_dispatch_choice = 2 # Input a grid power target for controller to try to achieve (i.e, keep grid purchases below 10 kW)
#batt.Battery.batt_dispatch_choice = 3 # Input a time series of battery powers (>0 for discharge, <0 for charge, for battery to try to meet)
#batt.Battery.batt_dispatch_choice = 4 # Manual discharge, based on prescribed periods where battery is allowed to charge or discharge, see SAM UI)


batt.execute()
print('Battery Average roundtrip efficiency: ' + str(batt.Outputs.average_battery_roundtrip_efficiency))

# Most of the time, 'gen' is in outputs, but battery model is currently not
utilityrate.SystemOutput.gen = batt.System.gen

# Net energy metering options
#utilityrate.UtilityRateFlat.ur_metering_option = 0 # single meter with monthly rollover credits in kWh
#utilityrate.UtilityRateFlat.ur_metering_option = 1 # single meter with monthly rollover credits in $
#utilityrate.UtilityRateFlat.ur_metering_option = 2 # single meter with no monthly rollover credits (net billing)
#utilityrate.UtilityRateFlat.ur_metering_option = 3 # single meter with monthly rollover credits in kWh (net billing)
#utilityrate.UtilityRateFlat.ur_metering_option = 4 # Two meters with all generation sold and all load purchased

utilityrate.execute()
print ('Electricity bill with system (yr 1): $' + str(utilityrate.Outputs.elec_cost_with_system[1]))
print ('Electricity bill without system (yr 1): $' + str(utilityrate.Outputs.elec_cost_without_system[1]))

loan.FinancialParameters.federal_tax_rate = [20]
loan.FinancialParameters.state_tax_rate = [5]
loan.SystemOutput.gen = utilityrate.SystemOutput.gen
loan.Cashloan.annual_energy_value = utilityrate.Outputs.annual_energy_value
loan.ThirdPartyOwnership.elec_cost_with_system = utilityrate.Outputs.elec_cost_with_system
loan.ThirdPartyOwnership.elec_cost_without_system = utilityrate.Outputs.elec_cost_without_system
loan.execute()
print ('NPV: $' + str(loan.Outputs.npv))
print ('Payback: ' + str(loan.Outputs.payback) + ' years')

