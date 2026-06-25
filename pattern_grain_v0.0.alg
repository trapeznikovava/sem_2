define res_len /* gamma_len */;
define init_steps /* init_steps */;

__in bit key[80];
__in bit iv[64];

bit LFSR[80];
bit NFSR[80];

__out bit result[res_len];

void shift_LFSR()
{
    __mem bit f = LFSR[0] ^ LFSR[13] ^ LFSR[23] ^ LFSR[38] ^ LFSR[51] ^ LFSR[62];
    int i;
    for(i = 0; i < 79; i = i + 1)
    {
        LFSR[i] = LFSR[i + 1];
    }
    LFSR[79] = f;
}

void shift_NFSR()
{
    __mem bit g1 = NFSR[63] ^ NFSR[60] ^ NFSR[52] ^ NFSR[45] ^ NFSR[37] ^ NFSR[33] ^ NFSR[28] ^ NFSR[21];
    __mem bit g2 = NFSR[15] ^ NFSR[9] ^ NFSR[0] ^ NFSR[63]&NFSR[60] ^ NFSR[37]&NFSR[33]^NFSR[15]&NFSR[9];
    __mem bit g3 = NFSR[60]&NFSR[52]&NFSR[45]^NFSR[33]&NFSR[28]&NFSR[21]^NFSR[63]&NFSR[45]&NFSR[28]&NFSR[9];
    __mem bit g4 = NFSR[60]&NFSR[52]&NFSR[37]&NFSR[33]^NFSR[63]&NFSR[60]&NFSR[21]&NFSR[15];
    __mem bit g5 = NFSR[63]&NFSR[60]&NFSR[52]&NFSR[45]&NFSR[37]^NFSR[33]&NFSR[28]&NFSR[21]&NFSR[15]&NFSR[9];
    __mem bit g6 = NFSR[52]&NFSR[45]&NFSR[37]&NFSR[33]&NFSR[28]&NFSR[21];
    __mem bit g = g1^g2^g3^g4^g5^g6;
    int i;
    for(i = 0; i < 79; i = i + 1)
    {
        NFSR[i] = NFSR[i + 1];
    }
    NFSR[79] = g ^ LFSR[0];
}

bit H(bit x0, bit x1, bit x2, bit x3, bit x4)
{
    return x1 ^ x4 ^ x0&x3 ^ x2&x3 ^ x3&x4 ^ x0&x1&x2 ^ x0&x2&x3 ^ x0&x2&x4 ^ x1&x2&x4 ^ x2&x3&x4;
}

void set_key_iv()
{
    int i;
    for(i = 0; i < 80; i = i + 1)
    {
        NFSR[i] = key[i];
    }
    for(i = 0; i < 64; i = i + 1)
    {
        LFSR[i] = iv[i];
    }
    for(i = 64; i < 80; i = i + 1)
    {
        LFSR[i] = 1;
    }
}

void main()
{
    set_key_iv();
    int i;
    for(i = 0; i < init_steps; i = i + 1)
    {
        bit out = NFSR[0] ^ H(LFSR[3], LFSR[25], LFSR[46], LFSR[64], NFSR[63]);
        shift_NFSR();
        shift_LFSR();
        NFSR[79] = NFSR[79] ^ out;
        LFSR[79] = LFSR[79] ^ out;
    }
    for(i = 0; i < res_len; i = i + 1)
    {
        bit output = NFSR[0] ^ H(LFSR[3], LFSR[25], LFSR[46], LFSR[64], NFSR[63]);
        shift_NFSR();
        shift_LFSR();
        result[i] = output;
    }
}