from mip import Model, xsum, minimize, BINARY
import numpy as np
from numpy import load
import math

######################################################################################################
# VESSELS DATA
######################################################################################################
# Number of vessels
# n_up = 3
n_down = 3

# Readiness times for vessels up
time_ready_up = [600, 630, 670]
time_ready_down = [600, 650, 680]

DL = 180  # Dar al menos 180 para evitar problemas de factibilidad
# Deadline times for vessels down
time_dead_up = [time_ready_up[0] + DL, time_ready_up[1] + DL, time_ready_up[2] + DL]
time_dead_down = [time_ready_down[0] + DL, time_ready_down[1] + DL, time_ready_down[2] + DL]

# Vessels beams
# beam_up = [1, 1, 1]
beam_down = [1, 1, 1]

# Vessels maximum speed
# vmax_up = [20, 20, 20]
vmax_down = [20, 20, 20]

# Vessels Draft
# draft_up = [7.5, 5, 5]
draft_down = [5, 7.5, 7.5]


######################################################################################################
# ETSII
######################################################################################################
def get_vessels_schedule(entry_vessels):
    entry_vessels_sorted_eta = sorted(entry_vessels, key=lambda x: x.eta, reverse=False)

    n_up = len(entry_vessels_sorted_eta)
    beam_up = [v.vessel_size for v in entry_vessels_sorted_eta]
    vmax_up = [v.vel_max for v in entry_vessels_sorted_eta]
    draft_up = [v.draught for v in entry_vessels_sorted_eta]

    etas_minutes_diff_sixminutale = [
        int(((entry_vessels_sorted_eta[i + 1].eta - entry_vessels_sorted_eta[
            i].eta).total_seconds() / 60) * 6)
        for i in range(0, len(entry_vessels_sorted_eta) - 1)]

    if len(etas_minutes_diff_sixminutale) != 0 or n_up == 1:
        etas_minutes_diff_sixminutale.insert(0, 0)

    time_ready_up = etas_minutes_diff_sixminutale

    DL = 180  # ventana de tiempo que el barco puede estar navegando por el río
    # Tiempo que el barco puede estar en el río
    time_dead_up = [tr + DL for tr in etas_minutes_diff_sixminutale]

    plan, tubes_up, tubes_down, n_tubes_up, n_tubes_down = planning(n_up, n_down, time_ready_up, time_ready_down,
                                                                    beam_up, beam_down, vmax_up, vmax_down, draft_up,
                                                                    time_dead_up)
    schedule_to_return = [p_i[0] for p_i in plan]

    # TODO esto es un work-around para que no falle en la demo, hay que arreglarlo con JUAN
    schedule_to_return = [0 if math.isnan(x) else x for x in schedule_to_return]

    computed_delay_minutes = [round((round(planned) - round(obtained)) / 6) for planned, obtained in
                              zip(schedule_to_return, time_ready_up + time_ready_down)]

    # print("INITIAL TIMES: ", time_ready_up + time_ready_down)
    # print("SCHEDULE TO RETURN: ", schedule_to_return)
    # print("COMPUTED DELAY MINUTES: ", computed_delay_minutes)

    computed_delay_minutes_up = computed_delay_minutes[:n_up]
    computed_delay_minutes_down = computed_delay_minutes[n_up:]

    for vi in range(len(entry_vessels_sorted_eta)):
        entry_vessels_sorted_eta[vi].new_planner_entry_time(computed_delay_minutes_up[vi])

    return entry_vessels_sorted_eta


######################################################################################################
# TUBES FUNDING FUNCTION (3 WWINDOW SIMPLIFICATION)
######################################################################################################
def tubes_finding(vessel_draft, t_ready, t_deadline, updown):
    # Import map of depth
    depth_map = load('./interventions/external_agent/depth_map.npy', allow_pickle=True)
    # Distances
    dist = [1.9, 1.4, 4.5, 2.2, 4.0, 5.2, 3.7, 6.4, 5.9, 5.4, 3.3, 5.2, 2.5, 6.2,
            1.8, 1.2, 3.4, 1.7, 2.0, 4.2, 3.0, 2.2, 4.8, 4.9]
    # Speed limits inverse
    speed_limits_inv = [1 / 10.1860, 1 / 16.6680, 1 / 16.6680, 1 / 17.5940, 1 / 17.5940, 1 / 18.5200,
                        1 / 21.2980, 1 / 21.2980, 1 / 21.2980, 1 / 22.2240, 1 / 22.2240, 1 / 22.2240,
                        1 / 19.4460, 1 / 19.4460, 1 / 22.2240, 1 / 18.5200, 1 / 21.2980, 1 / 23.1500,
                        1 / 23.1500, 1 / 23.1500, 1 / 22.2240, 1 / 18.5200, 1 / 21.2980, 1 / 21.2980]
    # Binary map of depth according to vessel draft
    # Binary map of depth according to vessel draft
    depth_map_bin = np.zeros([depth_map.shape[0], depth_map.shape[1]])
    for i in range(t_ready, t_deadline):
        for j in range(0, depth_map_bin.shape[1]):
            if abs(depth_map[i][j]) >= vessel_draft:
                depth_map_bin[i][j] = 1
    # plt.matshow(depth_map_bin);
    waypoints_tide = [1, 492, 869]

    # WINDOW 1
    w_1_entry = []
    w_1_exit = []
    w_1 = []
    for i in range(t_ready, t_deadline):
        if i == t_ready and depth_map_bin[i, 0] == 1:
            w_1_entry.append(i)
        if depth_map_bin[i, 0] == 0 and depth_map_bin[i + 1, 0] == 1:
            w_1_entry.append(i + 1)
    for i in range(t_ready, t_deadline):
        if depth_map_bin[i, 0] == 1 and depth_map_bin[i + 1, 0] == 0:
            w_1_exit.append(i)
        if i == t_deadline - 1 and depth_map_bin[i, 0] == 1:
            w_1_exit.append(i)
    for i in range(0, len(w_1_entry)):
        w_1.append([w_1_entry[i], w_1_exit[i]])

        # WINDOW 2
    w_2_entry = []
    w_2_exit = []
    w_2 = []
    for i in range(t_ready, t_deadline):
        if i == t_ready and depth_map_bin[i, 491] == 1:
            w_2_entry.append(i)
        if depth_map_bin[i, 491] == 0 and depth_map_bin[i + 1, 491] == 1:
            w_2_entry.append(i + 1)
    for i in range(t_ready, t_deadline):
        if depth_map_bin[i, 491] == 1 and depth_map_bin[i + 1, 491] == 0:
            w_2_exit.append(i)
        if i == t_deadline - 1 and depth_map_bin[i, 491] == 1:
            w_2_exit.append(i)
    for i in range(0, len(w_2_entry)):
        w_2.append([w_2_entry[i], w_2_exit[i]])

        # WINDOW 3
    w_3_entry = []
    w_3_exit = []
    w_3 = []
    for i in range(t_ready, t_deadline):
        if i == t_ready and depth_map_bin[i, 491] == 1:
            w_3_entry.append(i)
        if depth_map_bin[i, 491] == 0 and depth_map_bin[i + 1, 491] == 1:
            w_3_entry.append(i + 1)
    for i in range(t_ready, t_deadline):
        if depth_map_bin[i, 491] == 1 and depth_map_bin[i + 1, 491] == 0:
            w_3_exit.append(i)
        if i == t_deadline - 1 and depth_map_bin[i, 491] == 1:
            w_3_exit.append(i)
    for i in range(0, len(w_3_entry)):
        w_3.append([w_3_entry[i], w_3_exit[i]])

        # PATH ROUTING

    if updown == 0:
        # Path Building
        path_from_1_to_2 = []
        time_arrival_to_2_hist = []
        for i in range(0, len(w_1)):
            time_arrival_to_2 = w_1[i][0] + 10 * (np.dot(dist[0:12], speed_limits_inv[0:12]))
            time_arrival_to_2_hist.append(time_arrival_to_2)
            for j in range(0, len(w_2)):
                if time_arrival_to_2 <= w_2[j][1]:
                    path_from_1_to_2.append([w_1[i], [max(w_2[j][0], time_arrival_to_2), w_2[j][1]]])
        path_from_2_to_3 = []
        time_arrival_to_3_hist = []
        for i in range(0, len(path_from_1_to_2)):
            time_arrival_to_3 = path_from_1_to_2[i][1][0] + 10 * (np.dot(dist[12:24], speed_limits_inv[12:24]))
            time_arrival_to_3_hist.append(time_arrival_to_3)
            for j in range(0, len(w_3)):
                if time_arrival_to_3 <= w_3[j][1]:
                    path_from_2_to_3.append([path_from_1_to_2[i][0], path_from_1_to_2[i][1], w_3[j]])
    else:
        path_from_3_to_2 = []
        time_arrival_to_2_hist = []
        for i in range(0, len(w_3)):
            time_arrival_to_2 = w_3[i][0] + 10 * (np.dot(dist[12:24], speed_limits_inv[12:24]))
            time_arrival_to_2_hist.append(time_arrival_to_2)
            for j in range(0, len(w_2)):
                if time_arrival_to_2 <= w_2[j][1]:
                    path_from_3_to_2.append([w_3[i], [max(w_2[j][0], time_arrival_to_2), w_2[j][1]]])

        path_from_2_to_1 = []
        time_arrival_to_1_hist = []

        for i in range(0, len(path_from_3_to_2)):
            time_arrival_to_1 = path_from_3_to_2[i][1][0] + 10 * (np.dot(dist[0:12], speed_limits_inv[0:12]))
            time_arrival_to_1_hist.append(time_arrival_to_1)
            for j in range(0, len(w_1)):
                if time_arrival_to_1 <= w_1[j][1]:
                    path_from_2_to_1.append([path_from_3_to_2[i][0], path_from_3_to_2[i][1], w_1[j]])

    if updown == 0:
        tubes = path_from_2_to_3
    elif updown == 1:
        tubes = path_from_2_to_1

    return tubes


def planning(n_up, n_down, time_ready_up, time_ready_down, beam_up, beam_down, vmax_up, vmax_down, draft_up,
             time_dead_up):
    ###########################################################################
    # WATERWAY DATA
    ###########################################################################

    # Waterway data (km/10)
    waypoints = [1, 20, 34, 79, 101, 141, 193, 230, 294, 353, 407,
                 440, 492, 517, 570, 597, 609, 643, 660, 680, 722, 752,
                 774, 822, 871]
    # Distaces (km)
    dist = [1.9, 1.4, 4.5, 2.2, 4.0, 5.2, 3.7, 6.4, 5.9, 5.4, 3.3, 5.2, 2.5, 6.2,
            1.8, 1.2, 3.4, 1.7, 2.0, 4.2, 3.0, 2.2, 4.8, 4.9]

    # Speed_limits (km/h)
    speed_limits = [10.1860, 16.6680, 16.6680, 17.5940, 17.5940, 18.5200,
                    21.2980, 21.2980, 21.2980, 22.2240, 22.2240, 22.2240,
                    19.4460, 19.4460, 22.2240, 18.5200, 21.2980, 23.1500,
                    23.1500, 23.1500, 22.2240, 18.5200, 21.2980, 21.2980]
    # Width (small, medium, large, huge)
    width = [1, 4, 2, 4, 4, 4, 4, 4, 2, 2, 2, 1, 8, 1, 8, 4, 4, 4, 4, 4,
             1, 8, 1, 2]

    ###########################################################################
    # TUBE FINDING
    ###########################################################################
    # Tubes for vessels UP
    tubes_up = []
    n_tubes_up = []
    updown = 0
    print(n_up, n_down)
    for i in range(0, n_up):
        tubes = tubes_finding(draft_up[i], time_ready_up[i], time_dead_up[i], updown)
        tubes_up.append(tubes)
        n_tubes_up.append(len(tubes))
    tubes_down = []
    n_tubes_down = []
    updown = 1
    for i in range(0, n_down):
        tubes = tubes_finding(draft_down[i], time_ready_down[i], time_dead_down[i], updown)
        tubes_down.append(tubes)
        n_tubes_down.append(len(tubes))

        ###########################################################################
        # OPTIMIZATION PROBLEM
    ###########################################################################

    # Model Creation
    m = Model(sense=minimize, solver_name='GRB')

    # Time varibales
    t_u = [[m.add_var() for i in range(0, len(waypoints))] for j in range(0, n_up)]
    t_d = [[m.add_var() for i in range(0, len(waypoints))] for j in range(0, n_down)]

    #  Crossing variable
    c = [[m.add_var(var_type=BINARY) for i in range(0, len(waypoints))] for j in range(0, n_up * n_down)]

    # Route variables
    r_up = [m.add_var(var_type=BINARY) for i in range(0, np.sum(n_tubes_up))]
    r_down = [m.add_var(var_type=BINARY) for i in range(0, np.sum(n_tubes_down))]

    # Cost function
    m.objective = minimize(xsum(t_u[i][len(waypoints) - 1] - t_u[i][0] for i in range(0, n_up))
                           + xsum(t_d[i][0] - t_d[i][len(waypoints) - 1] for i in range(0, n_down))
                           + xsum(t_u[i][0] - time_ready_up[i] for i in range(0, n_up))
                           + xsum(t_d[i][len(waypoints) - 1] - time_ready_down[i] for i in range(0, n_down)))

    # Speed constraints
    for i in range(0, n_up):
        for j in range(0, len(waypoints) - 1):
            m += min(vmax_up[i], speed_limits[j]) * (t_u[i][j + 1] - t_u[i][j]) / 10 >= dist[j]
    for i in range(0, n_down):
        for j in range(0, len(waypoints) - 1):
            m += min(vmax_down[i], speed_limits[j]) * (t_d[i][j] - t_d[i][j + 1]) / 10 >= dist[j]

            # Routes constraints
    M = 1000000
    route_points = [0, 12, 24]
    for i in range(0, n_up):
        for j in range(0, n_tubes_up[i]):
            indice = int(np.sum(n_tubes_up[0:i]) + j)
            for p in range(0, len(route_points)):
                m += t_u[i][route_points[p]] + (1 - r_up[indice]) * M >= tubes_up[i][j][p][0]
                m += t_u[i][route_points[p]] <= tubes_up[i][j][p][1] + (1 - r_up[indice]) * M
    for i in range(0, len(n_tubes_up)):
        m += xsum(r_up[j] for j in range(sum(n_tubes_up[0:i]), sum(n_tubes_up[0:i + 1]))) == 1

    route_points = [24, 12, 0]
    for i in range(0, n_down):
        for j in range(0, n_tubes_down[i]):
            indice = int(np.sum(n_tubes_down[0:i]) + j)
            for p in range(0, len(route_points)):
                m += t_d[i][route_points[p]] + (1 - r_down[indice]) * M >= tubes_down[i][j][p][0]
                m += t_d[i][route_points[p]] <= tubes_down[i][j][p][1] + (1 - r_down[indice]) * M
    for i in range(0, len(n_tubes_down)):
        m += xsum(r_down[j] for j in range(sum(n_tubes_down[0:i]), sum(n_tubes_down[0:i + 1]))) == 1

    # Crossing constraints
    for i in range(0, n_up):
        for j in range(0, n_down):
            index = n_down * i + j
            for p in range(0, len(waypoints)):
                m += t_u[i][p] <= t_d[j][p] + M * xsum(c[index][l] for l in range(0, p))
                m += t_d[j][p] <= t_u[i][p] + M * (1 - xsum(c[index][l] for l in range(0, p)))
    for i in range(0, n_up):
        for j in range(0, n_down):
            index = n_down * i + j
            m += xsum(c[index][l] for l in range(0, len(waypoints))) <= 1

    # Width constraints
    for i in range(0, n_up):
        for j in range(0, n_down):
            for k in range(0, len(width)):
                index = n_down * i + j
                if beam_up[i] + beam_down[j] >= width[k]:
                    m += c[index][k] == 0
                    # Optimization
    m.optimize()

    # Solution
    plan = np.zeros((n_up + n_down, len(waypoints)))
    for i in range(0, n_up + n_down):
        for j in range(0, len(waypoints)):
            plan[i][j] = m.vars[len(waypoints) * (i) + j].x
    return plan, tubes_up, tubes_down, n_tubes_up, n_tubes_down


'''
#####################################################################################################
# TEST
#####################################################################################################
waypoints = [1, 20, 34, 79, 101, 141, 193, 230, 294, 353, 407,
             440, 492, 517, 570, 597, 609, 643, 660, 680, 722, 752,
             774, 822, 871]
[plan, tubes_up, tubes_down, n_tubes_up, n_tubes_down] = planning(n_up, n_down, time_ready_up, time_ready_down, beam_up,
                                                                  beam_down, vmax_up, vmax_down)
for i in range(0, n_up + n_down):
    plt.plot(waypoints, plan[i, 0:len(waypoints)], '--', linewidth=1.5)
    plt.grid(True)
    plt.xlabel('Position (km/10)')
    plt.ylabel('Time (km/10)')
'''
