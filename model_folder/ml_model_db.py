from argparse import ArgumentParser
import numpy as np
from sys import exit
import scipy
import scipy.stats
import itertools
from math import sqrt
from scipy.optimize import minimize
import json
import pickle
import os
import psycopg2
import pandas.io.sql as sqlio


get_local_path = lambda s: os.path.join(os.path.dirname(os.path.realpath(__file__)), s)

def connect():
    connection = None
    try:
        connection = psycopg2.connect( host = "127.0.0.1", database="WeBuildAi_development")
        print("Connection Successful")
    except Exception:
        print("Connection ERROR")
        exit(0)

    return connection

def get_possible_feature_values(connection):
    cursor = connection.cursor()
    query = "SELECT * from categorical_data_options"
    df = sqlio.read_sql_query(query, connection)

    possible_values = {}

    data_range_id_values = df['data_range_id'].values
    option_values = df['option_value'].values

    for i in range(len(option_values)):
        try:
            possible_values[int(data_range_id_values[i])].append(option_values[i])
        except KeyError as e:
            possible_values[int(data_range_id_values[i])] = [option_values[i]]

    return possible_values

def convert_categorical_features(feature):
    value = feature['feat_value']
    possible_values = feature['possible_values']

    if (("High" in possible_values) and ("Med" in possible_values) and ("Low" in possible_values)):
        if value == "High":
            mod_value = 1.0
        elif value == "Med":
            mod_value = 0.5
        elif value == "Low":
            mod_value = 0.0

        return mod_value

    elif (("Yes" in possible_values) and ("No" in possible_values)):
        if value == "Yes":
            mod_value = 1.0
        elif value == "No":
            mod_value = 0.0

        return mod_value

    else:
        arr = [0.0] * len(possible_values)
        arr[possible_values.index(value)] = 1.0

    return arr

def scale(feature, is_scale):
    '''
	:param feature: JSON object for the feature
	:param is_scale: Whether to scale OR not.
	:return: scaled OR unscaled value of the feature
	'''
    if (feature['feat_type'] == 'categorical'):
        mod_feature = convert_categorical_features(feature)
        return mod_feature
    else:
        value = float(feature['feat_value'])
        if (is_scale == False):
            mod_value = float(value)
        elif ((is_scale == True) and (feature['feat_type'] == 'continuous')):
            mod_value = float(value)
            mod_value = (value - float(feature['feat_min'])) / (float(feature['feat_max']) - float(feature['feat_min']))
        else:
            print("Not Implemented Yet- Scale")
            exit(0)

    return mod_value

def get_scenarios(connection, pid, pairwise_type, possible_values, is_scale):
    data = {}
    data['part_id']=int(pid)
    data['type']=pairwise_type

    cursor = connection.cursor()

    # This should be used.

    query = """
    SELECT participant_id, scenario_1, scenario_2, choice, reason, category 
    FROM pairwise_comparisons a WHERE participant_id=%s AND category='%s'
    """%(str(pid), str(pairwise_type))

    '''
    query = """
    SELECT participant_id, scenario_1, scenario_2, choice, reason, category
    FROM pairwise_comparisons WHERE participant_id=%s AND choice IS NOT NULL
    """%(str(pid))
    '''

    cursor.execute(query)

    data_arr = []
    imp_features = set()

    feature_array1 = []  # Values for feature array1
    feature_array2 = []  # Values for feature array2

    all_samples = []

    scenario_counter = 0
    for record in cursor:
        scenario_counter+=1
        scenarios = {}

        scenario_1 = record[1]
        scenario_2 = record[2]
        choice = record[3]
        reason = record[4]

        cursor2 = connection.cursor()
        query2 = '''
                    SELECT a.group_id, a.feature_id, a.feature_value, 
                    b.id AS featureId, b.name AS featureName, b.description AS description, b.category AS feat_category, 
                    b.active AS active, b.company AS company, c.is_categorical AS categories, c.lower_bound as lb, 
                    c.upper_bound as ub
                    FROM scenarios a, features b, data_ranges c
                    WHERE a.group_id=%s AND b.id = a.feature_id
                    AND c.feature_id = a.feature_id;
                    '''%(str(scenario_1))
        cursor2.execute(query2)

        scenario1_arr = []

        for row in cursor2:
            feature_obj = {}

            feature_id = int(row[1])
            feature_value = row[2]
            feature_name = row[4]
            feature_desc = row[5]
            feature_category = row[6]
            feature_active = row[7]
            feature_company = row[8]
            feature_type = row[9]
            if(feature_type==True):
                feature_type = "categorical"
            elif(feature_type==False):
                feature_type = "continuous"
            feature_min = row[10]
            feature_max = row[11]

            feature_obj['feat_id'] = feature_id
            feature_obj['feat_name'] = feature_name
            feature_obj['feat_category'] = feature_category
            feature_obj['feat_value'] = feature_value
            feature_obj['feat_type'] = feature_type
            if(feature_type=='categorical'):
                f_poss_values = possible_values[feature_id]
            else:
                f_poss_values = []
            feature_obj['possible_values'] = f_poss_values
            feature_obj['feat_min'] = feature_min
            feature_obj['feat_max'] = feature_max

            scenario1_arr.append(feature_obj)
            imp_features.add(feature_id)
        scenarios['scenario_1'] = scenario1_arr

        cursor3 = connection.cursor()
        query3 = '''
                    SELECT a.group_id, a.feature_id, a.feature_value, 
                    b.id AS featureId, b.name AS featureName, b.description AS description, b.category AS feat_category, 
                    b.active AS active, b.company AS company, c.is_categorical AS categories, c.lower_bound as lb, 
                    c.upper_bound as ub
                    FROM scenarios a, features b, data_ranges c
                    WHERE a.group_id=%s AND b.id = a.feature_id
                    AND c.feature_id = a.feature_id;
                    ''' % (str(scenario_2))
        cursor3.execute(query3)

        scenario2_arr = []
        for row in cursor3:
            feature_obj = {}

            feature_id = int(row[1])
            feature_value = row[2]
            feature_name = row[4]
            feature_desc = row[5]
            feature_category = row[6]
            feature_active = row[7]
            feature_company = row[8]
            feature_type = row[9]
            if (feature_type == True):
                feature_type = "categorical"
            elif (feature_type == False):
                feature_type = "continuous"
            feature_min = row[10]
            feature_max = row[11]

            feature_obj['feat_id'] = feature_id
            feature_obj['feat_name'] = feature_name
            feature_obj['feat_category'] = feature_category
            feature_obj['feat_value'] = feature_value
            feature_obj['feat_type'] = feature_type
            if (feature_type == 'categorical'):
                f_poss_values = possible_values[feature_id]
            else:
                f_poss_values = []
            feature_obj['possible_values'] = f_poss_values
            feature_obj['feat_min'] = feature_min
            feature_obj['feat_max'] = feature_max

            scenario2_arr.append(feature_obj)
        scenarios['scenario_2'] = scenario2_arr
        scenarios['choice'] = choice

        data_arr.append(scenarios)

        scenario_1 = scenario1_arr  # Features corresp. to option 1
        scenario_2 = scenario2_arr  # Features corresp. to option 2

        scenario_1 = sorted(scenario_1, key=lambda elem: elem["feat_id"])
        scenario_2 = sorted(scenario_2, key=lambda elem: elem["feat_id"])

        num_features1 = len(scenario_1)
        num_features2 = len(scenario_2)

        feat_ids1 = []  # Feature ids - to check if we are comparing apples and apples
        feat_ids2 = []

        array_1 = []  # Actual Values
        array_2 = []

        for f1 in scenario_1:
            feat_ids1.append(f1['feat_id'])  # Makes sense.

            modified_features = scale(f1, is_scale)

            if (type(modified_features) is list):
                for mf in modified_features:
                    array_1.append(mf)
            else:
                array_1.append(modified_features)

            imp_features.add(f1['feat_id'])
        feature_array1.append(feat_ids1)

        for f2 in scenario_2:
            feat_ids2.append(f2['feat_id'])

            modified_features = scale(f2, is_scale)
            if (type(modified_features) is list):
                for mf in modified_features:
                    array_2.append(mf)
            else:
                array_2.append(modified_features)

            imp_features.add(f2['feat_id'])
        feature_array2.append(feat_ids2)

        all_samples.append([array_1, array_2, choice])

    print("Number of Scenarios="+str(scenario_counter))
    return all_samples, imp_features

def split_train_test(compars, test_frac, feat_trans):
    n = len(compars)
    np.random.shuffle(compars)

    n_test = int(test_frac * n)
    n_train = n - n_test

    train_comps = compars[:n_train, :, :]
    test_comps = compars[n_train:, :, :]

    k_train_comps = []
    #print("Train="+str(train_comps.shape))
    #print("Test="+str(test_comps.shape))

    for j in range(n_train):
        altA = train_comps[j, 0, :]
        altA = list(altA)
        altA.append(1)
        k_altA = []
        for t in feat_trans:
            this_prod = 1
            for index in t:
                this_prod *= altA[index]
            k_altA.append(this_prod)

        altB = train_comps[j, 1, :]
        altB = list(altB)
        altB.append(1)
        k_altB = []
        for t in feat_trans:
            this_prod = 1
            for index in t:
                this_prod *= altB[index]
            k_altB.append(this_prod)

        k_train_comps.append([k_altA, k_altB])
    k_train_comps = np.array(k_train_comps)

    k_test_comps = []
    for j in range(n_test):
        altA = test_comps[j, 0, :]
        altA = list(altA)
        altA.append(1)
        k_altA = []
        for t in feat_trans:
            this_prod = 1
            for index in t:
                this_prod *= altA[index]
            k_altA.append(this_prod)

        altB = test_comps[j, 1, :]
        altB = list(altB)
        altB.append(1)
        k_altB = []
        for t in feat_trans:
            this_prod = 1
            for index in t:
                this_prod *= altB[index]
            k_altB.append(this_prod)

        k_test_comps.append([k_altA, k_altB])
    k_test_comps = np.array(k_test_comps)

    return k_train_comps, k_test_comps, n_train, n_test

def run_model(args):
    connection = connect()
    pid = args.pid
    pairwise_type = args.type
    data_type = args.d
    normalize = args.n
    k = args.k
    loss_fun = args.l
    num_iters = args.num
    size_type = args.sz
    test_frac = args.tf

    possible_values = get_possible_feature_values(connection)
    data, imp_features = get_scenarios(connection, pid, pairwise_type, possible_values, is_scale=True)

    lambda_reg = 1
    d = len(imp_features)

    print("Dimension d="+str(d))
    feat_trans = set([])
    feat_trans_dup = list(itertools.product(range(d + 1), repeat=k))
    for t in feat_trans_dup:
        feat_trans.add(tuple(sorted(t)))

    feat_trans = list(feat_trans)
    feat_trans.remove(tuple([d] * k))

    N = 1
    d_ext = len(feat_trans)
    learnt_beta = np.zeros((N, d_ext))

    compars = []
    for i in range(len(data)):
        altA = data[i][0]
        altB = data[i][1]
        choice = data[i][2]

        if (choice == 'A'):
            compars.append(np.array([altA, altB]))
        else:
            compars.append(np.array([altB, altA]))

    print("PRINTING SHAPE OF EACH ROW")
    for x in compars:
        print(x.shape)
    print("STOPPING...")

    compars = np.array(compars)
    print("Length of comparisons=" + str(len(compars)))

    for iter in range(num_iters):
        total_num_correct = 0
        total_test_compars = 0
        total_soft_loss = 0

        # compars[j,0,:] is first alternative of comparison j, and compars[j,1,:] is the other.
        # Storing such that the 0 alternative is chosen over 1 alternative.

        k_train_comps, k_test_comps, n_train, n_test = split_train_test(compars, test_frac, feat_trans)

        # ETA = 0.00000001	# Learning rate
        # EPS = 0.00005	# Stopping criteria parameter
        THRES = 0.00001  # Threshold for cdf value. If smaller than this, then just use this

        # Learn parameters of voter i using his comparisons, by gradient descent
        this_diff = np.zeros((n_train, d_ext))

        for j in range(n_train):  # Pre-compute X_j - Z_j and store
            this_diff[j, :] = k_train_comps[j, 0, :] - k_train_comps[j, 1, :]

        this_beta = np.random.uniform(-0.001, 0.001,
                                      d_ext)  # Initialize parameter randomly	# Could instead use np.zeros(d), since it's a convex program

        '''
            REGULARIZATION
        '''

        def normal_likeli(beta):  # negative of the log-likelihood
            # print(f'normal likeli: {-np.sum(scipy.stats.norm.logcdf(np.dot(this_diff, beta)))}')

            # L2 regularization
            reg_penalty = lambda_reg * np.dot(beta, beta)

            return -np.sum(scipy.stats.norm.logcdf(np.dot(this_diff, beta))) - reg_penalty

        def der_normal_likeli(beta):
            dot_prod = np.dot(this_diff, beta)
            pdfs = scipy.stats.norm.pdf(dot_prod)
            cdfs = scipy.stats.norm.cdf(dot_prod)

            grad = np.zeros(d_ext)
            for j in range(n_train):
                grad += this_diff[j] * pdfs[j] / (max(cdfs[j], THRES))

            # print(f'normal grad: {grad}')
            reg_penalty = 2 * np.sum(beta)

            return -grad - reg_penalty

        def logistic_likeli(beta):  # negative of the log-likelihood
            return np.sum(np.log(1 + np.exp(-np.dot(this_diff, beta))))

        def der_logistic_likeli(beta):
            dot_prod = np.dot(this_diff, beta)

            grad = np.zeros(d_ext)
            for j in range(n_train):
                grad += this_diff[j] * np.exp(-dot_prod[j]) / (1 + np.exp(-dot_prod[j]))

            return -grad

        if (loss_fun == 'normal'):
            likeli = normal_likeli
            der_likeli = der_normal_likeli
        elif (loss_fun == 'logistic'):
            likeli = logistic_likeli
            der_likeli = der_logistic_likeli

        res = minimize(likeli, this_beta, method='BFGS', jac=der_likeli, options={'gtol': 1e-10, 'disp': False})
        this_beta = res.x

        # print("Learnt parameters for " + data_files[i] + ":", this_beta, '\n')
        learnt_beta[0, :] = this_beta

    TEST_SET = np.vstack((k_train_comps, k_test_comps))
    print(TEST_SET.shape)

    soft_loss, num_correct, n_test = test(this_beta, np.vstack((k_train_comps, k_test_comps)), n_test, pid, loss_fun,
                                          size_type, test_frac)
    print("FINAL LEARNT BETA")
    print(this_beta)

    print("Soft LOSS=" + str(soft_loss))
    print("Accuracy=" + str(float(num_correct) / n_test))

    #filename = inp_file.split("/")[::-1][0]
    filename = str(pid)+"_"+str(pairwise_type)
    print(filename)

    pickle.dump(this_beta,
                open(get_local_path("RESULT/betas/Participant_" + str(filename) + "_BETA_Round1.pkl"),
                     'wb'))

    # Potentiall include the code here for the weight vector
    return this_beta, soft_loss, num_correct, n_test

def test(this_beta, k_test_comps, n_test, pid, loss_fun, size_type, test_frac):
    num_correct = 0
    soft_loss = 0
    incorrect_comps = []
    correct_comps = []

    for j in range(n_test):
        mean_util_0 = np.dot(this_beta, k_test_comps[j, 0, :])
        mean_util_1 = np.dot(this_beta, k_test_comps[j, 1, :])

        prob_0_beats_1 = scipy.stats.norm.cdf(mean_util_0 - mean_util_1, scale=2)

        if (mean_util_0 > mean_util_1):
            num_correct += 1
            correct_comps.append([list(k_test_comps[j, 0, :]), list(k_test_comps[j, 1, :])])
        else:
            incorrect_comps.append([list(k_test_comps[j, 0, :]), list(k_test_comps[j, 1, :])])

        soft_loss += (1 - prob_0_beats_1) ** 2

    if (len(incorrect_comps) > 0):
        incorrect_comps_filename = get_local_path(
            "RESULT/incorrect_comps/Participant_" + str(pid) + "_" + str(loss_fun) + "_" + str(size_type) + "_" + str(
                int(test_frac) * 100) + "_errors.txt")
        with open(incorrect_comps_filename, 'w') as incorrect_outfile:
            for incorrect_comp in incorrect_comps:
                incorrect_outfile.write(str(incorrect_comp))
                incorrect_outfile.write('\n')

    # write correct comparisons out to file
    if len(correct_comps) > 0:
        correct_comps_filename = get_local_path(
            "RESULT/correct_comps/Participant_" + str(pid) + "_" + str(loss_fun) + "_" + str(size_type) + "_" + str(
                int(test_frac) * 100) + "_correct.txt")
        with open(correct_comps_filename, 'w') as correct_outfile:
            for correct_comp in correct_comps:
                correct_outfile.write(str(correct_comp))
                correct_outfile.write('\n')

    print("soft loss=" + str(soft_loss) + " accuracy=" + str(float(num_correct) / float(n_test)))
    return soft_loss, num_correct, n_test

if __name__ == '__main__':
    parser = ArgumentParser(description="Inputs.")
    parser.add_argument('-pid', type=str, default='None', help='participant_id')
    parser.add_argument('-type', type=str, default='driver', help='Running model for social/individual preferences')
    parser.add_argument('-d', type=str, default='D', help='data type (str)')
    parser.add_argument('-n', type=int, default=1, help='normalize features (int)')
    parser.add_argument('-k', type=int, default=1, help='degree of polynomial (int)')
    parser.add_argument('-l', type=str, default='normal', help='loss function(str')
    parser.add_argument('-num', type=int, default=100, help='value of num iters>0 (int)')
    parser.add_argument('-sz', type=str, default='cardinalsizes', help='size type (str)')
    parser.add_argument('-tf', type=float, default=0.5, help='test frac (float)')
    args = parser.parse_args()

    run_model(args)
