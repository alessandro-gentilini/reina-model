import json
import flask
import hashlib
from flask import session
from contextlib import contextmanager


# Variables
VARIABLE_DEFAULTS = {
    'area_name': 'HUS',
    'country': 'Finland',
    'max_age': 100,
    'simulation_days': 365,
    'start_date': '2020-02-18',
    'hospital_beds': 2600,
    'icu_units': 300,

    #
    # Disease parameters
    #

    # Chance to be asymptomatic
    'p_asymptomatic': 50.0,  # %

    # Overall chance to become infected after being exposed.
    # This is modified by viral load of the infector, which
    # depends on the day of the illness.
    'p_infection': 28.0,  # %

    # Chance to die after regular hospital care
    'p_hospital_death': 0.0,  # %
    # Chance to die after ICU care
    'p_icu_death': [
        [0, 40.0],
        [10, 40.0],
        [20, 50.0],
        [30, 50.0],
        [40, 50.0],
        [50, 50.0],
        [60, 50.0],
        [70, 50.0],
        [80, 50.0]
    ],
    # Chance to die if no hospital beds are available (but not
    # needing ICU care)
    'p_hospital_death_no_beds': 20.0,  # %
    # Chance to die if no ICU care units are available
    'p_icu_death_no_beds': 100.0,  # %

    # Mean number of days of being ill
    'mean_illness_duration': 7.0,
    # Average number of days of being hospitalized for people with
    # only severe symptoms
    'mean_hospitalization_duration': 14.0,

    # Average number of days in regular hospital bed before being
    # transferred to ICU for patients with critical symptoms.
    'mean_hospitalization_duration_before_icu': 3.0,
    # Average number of ICU care days
    'mean_icu_duration': 21.0,


    # Chance to be detected if showing mild symptoms but testing
    # is only for severe cases (might apply to e.g. healthcare workers)
    'p_detected_anyway': 25.0,  # %

    # Ratio of all infected people that require hospitalization
    # (more than mild symptoms) by age group
    # Source: https://www.medrxiv.org/content/10.1101/2020.03.09.20033357v1.full.pdf
    'p_severe': [
        [0, 0.0],
        [10, 0.0408],
        [20, 1.04],
        [30, 3.43],
        [40, 4.25],
        [50, 8.16],
        [60, 11.8],
        [70, 16.6],
        [80, 18.4]
    ],
    # Ratio of hospitalized cases requiring critical (ICU) care
    # Source: https://www.imperial.ac.uk/media/imperial-college/medicine/sph/ide/gida-fellowships/Imperial-College-COVID19-NPI-modelling-16-03-2020.pdf
    'p_critical': [
        [0, 5.0],
        [10, 5.0],
        [20, 5.0],
        [30, 5.0],
        [40, 6.3],
        [50, 12.2],
        [60, 27.4],
        [70, 43.2],
        [80, 70.9]
    ],
    'interventions': [
        ['test-all-with-symptoms', '2020-02-20'],
        ['test-only-severe-symptoms', '2020-03-15'],

        ['limit-mass-gatherings', '2020-03-12', 50],

        ['limit-mobility', '2020-03-12', 10],
        ['limit-mobility', '2020-03-17', 20],
        ['limit-mobility', '2020-03-20', 30],
        ['limit-mobility', '2020-03-22', 35],
        ['limit-mobility', '2020-03-28', 50],

        ['build-new-icu-units', '2020-04-30', 150],
        ['build-new-icu-units', '2020-05-30', 150],

        # FIXME: Fully remove import interventions
        ['import-infections', '2020-02-22', 5],
        ['import-infections', '2020-03-05', 20],
        ['import-infections', '2020-03-07', 40],
        ['import-infections', '2020-03-09', 30],
        ['import-infections', '2020-03-11', 20],
        ['import-infections', '2020-03-13', 20],
        ['import-infections', '2020-03-15', 20],
    ],

    'preset_scenario': 'default',

    # Used for sampling the model
    'sample_limit_mobility': 0,
    # Used for Monte Carlo simulation
    'random_seed': 0
}


# Make a hash of the default variables so that when they change,
# we will reset everybody's custom session variables.
DEFAULT_VARIABLE_HASH = hashlib.md5(json.dumps(VARIABLE_DEFAULTS).encode('utf8')).hexdigest()

_allow_variable_set = False


def set_variable(var_name, value):
    assert var_name in VARIABLE_DEFAULTS
    assert isinstance(value, type(VARIABLE_DEFAULTS[var_name]))

    if not flask.has_request_context():
        if not _allow_variable_set:
            raise Exception('Should not set variable outside of request context')
        VARIABLE_DEFAULTS[var_name] = value
        return

    if value == VARIABLE_DEFAULTS[var_name]:
        if var_name in session:
            del session[var_name]
        return

    session[var_name] = value


def get_variable(var_name, var_store=None):
    out = None

    if var_store is not None:
        out = var_store.get(var_name)
    elif flask.has_request_context():
        if session.get('default_variable_hash', '') != DEFAULT_VARIABLE_HASH:
            reset_variables()
        if var_name in session:
            out = session[var_name]

    if out is None:
        out = VARIABLE_DEFAULTS[var_name]

    if isinstance(out, list):
        # Make a copy
        return list(out)

    return out


def reset_variable(var_name):
    if flask.has_request_context() and var_name in session:
        del session[var_name]


def reset_variables():
    session['default_variable_hash'] = DEFAULT_VARIABLE_HASH
    for var_name in VARIABLE_DEFAULTS.keys():
        if var_name not in session:
            continue
        del session[var_name]


@contextmanager
def allow_set_variable():
    global _allow_variable_set

    old = _allow_variable_set
    _allow_variable_set = True
    try:
        yield None
    finally:
        _allow_variable_set = old
