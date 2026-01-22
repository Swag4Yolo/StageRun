CONSTANTS:

# PAD CONSTANTS
MODE_PAD       =  0
MODE_PADTO     =  1
MODE_PADTTERN  =  2
MODE_VAR       =  3


# CONDITIONAL CONSTANTS

EQUALS          = 0
GREATER_EQUALS  = 1
LOWER_EQUALS    = 2
GREATER         = 3
LOWER           = 4


Micro Instruction List:

# Processors
- initialize_pad_ni(next_flow_id, mode, value, num_bytes):
- pattern_res(total_range, program_id, pkt_cntr, pattern_result_1, pattern_result_2)
- sum_ni(next_flow_id, const_val, header_id, header_update, var_id, var_update)

# Fetchers
- fetch_ipv4_ttl(var_to_header, header_to_var, external_var_update)
- fetch_ipv4_dst(var_to_header, header_to_var, external_var_update)
- fetch_ipv4_src(var_to_header, header_to_var, external_var_update)
- fetch_ipv4_total_len(var_to_header, header_to_var, external_var_update)
- fetch_ipv4_protocol(var_to_header, header_to_var, external_var_update)
- fetch_tcp_ack_no(var_to_header, header_to_var, external_var_update)
- fetch_tcp_seq_no(var_to_header, header_to_var, external_var_update)
- fetch_tcp_flags(var_to_header, header_to_var, external_var_update)
- fetch_ipv4_identification(var_to_header, header_to_var, external_var_update)

# Conditional Processing
conditional_v1_v2(next_flow_id, mode, val, mode_2, val_2)
conditional_v3_v4(next_flow_id, mode, val, mode_2, val_2)
conditional_between_vars(next_flow_id, mode, mode_2) 

# Forward
fwd_ni(next_flow_id, port, qid, mark_to_drop, rts, enabled)


.pad.pattern (arg1:int, arg2:int, ..., argn:int):

    initialize_pad_ni(mode=MODE_PADTTERN)
    pattern_res(total_range=[0, arg1], pattern_result_1=arg1)
    ...
    pattern_res(total_range=[argn-1, argn], pattern_result_1=argn)

Description: "Pads a packet until a certain pattern. Example: '.pad.pattern #1500, #1600' pads a packet until the most approximate size. This StageRun instruction is divided into an initialize_pad_ni which initializes the padding mechanism with the necessary mode, and then it inserts the correct patterns, so that the Pad Mechanism knows how to process the packet later."

.load (lvalue: Header | Hash | Var, rvalue: Header | Var)
    if lvalue is Header and rvalue is Var:
        case lvalue: 'IPV4.TTL'  : fetch_ipv4_ttl(header_to_var=1)
        case lvalue: 'IPV4.DST'  : fetch_ipv4_dst(header_to_var=1)
        case lvalue: 'IPV4.SRC'  : fetch_ipv4_src(header_to_var=1)
        case lvalue: 'IPV4.LEN'  : fetch_ipv4_total_len(header_to_var=1)
        case lvalue: 'IPV4.PROTO': fetch_ipv4_protocol(header_to_var=1)
        case lvalue: 'TCP.ACK_NO': fetch_tcp_ack_no(header_to_var=1)
        case lvalue: 'TCP.SEQ_NO': fetch_tcp_seq_no(header_to_var=1)
        case lvalue: 'TCP.FLAGS' : fetch_tcp_flags(header_to_var=1)
        case lvalue: 'IPV4.ID'   : fetch_ipv4_identification(header_to_var=1)

        sum_ni(var_id=rvalue, var_update=1)

Description: "Loads a {Header, Hash, Var} into a {Header, Var}. When we load an header to a variable the engine internally knowns the var_id at which that Program Variable corresponds to."
        
.br.cond  (op, lvalue: Var, rvalue: Var | int, op2, lvalue2: Var, rvalue2: Var | int)
    if rvalue is Var:
        conditional_between_vars(mode=mode) 

    if rvalue is int:
        #options
        case mode: EQUALS           => res = 0
        case mode: GREATER_EQUALS   => res <= 0
        case mode: LOWER_EQUALS     => res >= 0
        case mode: GREATER          => res < 0
        case mode: LOWER            => res > 0
 
        conditional_v1_v2(op=op, mode=mode, res=res)
        conditional_v3_v4(op=op, mode=mode, res=res)

Description: "Performs a conditional with a specified mode and with arguments. It can support up to 4 arguments, where the right values of the expression can either be variables or constants. The second expression behaves similarly to the first expression."        

.jmp     (label: str)
    fwd_ni(next_flow_id=label_id(label), enabled=0)

Description: "Jump allows to change the current flow_id of a program by specifing the label name. Internally the label name is converted to the label identifier. The forwarding mechanism is disabled, which results in the packet not changing previous forwarding directions."

        
.fwd.enqjmp (port, qid, label) 
    fwd_ni(next_flow_id=label_id(label), port=port, qid=qid, enabled=1)


Description: "Fwd.enqjmp allows to forward a packet to a specific port and queue."





#############################################
#               OLD NOTATION                #
#############################################

#______________________________#
.load IPV4.IHL, $ihl
.load HASH.H1, $tmp
.load IPV4.IHL, $ihl

HASHTOVAR syn_cookie -> tmp;
VTOHEADER tmp -> TCP.SEQNO;
HTOVAR IPV4.IHL -> ihl;
#______________________________#


# OLD StageRun

IGTS -> time;
MSET dns_checker[four_tuple] 1;
MINC numBytesFlow[flow_key] PKT.SIZE -> oldNBytes (OLD);
MGET numBytesFlow[flow_key] PKT.SIZE -> oldNBytes (NEW);
DROP;
FWD;
FWD_AND_ENQUEUE;
HINC IPV4.TTL -1;
HASSIGN IPV4.DST "192.168.1.1";
ARIT ihl * 4 -> ihl;
ARIT ihl + tmp -> tmp;

IN label;
OUT label;
IF label == 1:

HARIT TCP.SEQNO + 1 -> TCP.ACKNO;
# Set flags = SYN+ACK
HASSIGN TCP.FLAGS 12; # pass ack flag
RTS;


IF checker == 1 && result_time < 4000: #Convert to seconds
    FWD pToExternal;
ENDIF