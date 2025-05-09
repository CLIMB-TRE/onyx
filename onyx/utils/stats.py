# ruff: noqa
# import basecount


# This function was written by Heng Li
# https://github.com/lh3/readfq
def readfq(fp):  # this is a generator function
    last = None  # this is a buffer keeping the last unprocessed line
    while True:  # mimic closure; is it a bad idea?
        if not last:  # the first record or a record following a fastq
            for l in fp:  # search for the start of the next record
                if l[0] in ">@":  # fasta/q header line
                    last = l[:-1]  # save this line
                    break
        if not last:
            break
        name, seqs, last = last[1:].partition(" ")[0], [], None
        for l in fp:  # read the sequence
            if l[0] in "@+>":
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != "+":  # this is a fasta record
            yield name, "".join(seqs), None  # yield a fasta record
            if not last:
                break
        else:  # this is a fastq record
            seq, leng, seqs = "".join(seqs), 0, []
            for l in fp:  # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq):  # have read enough quality
                    last = None
                    yield name, seq, "".join(seqs)
                    # yield a fastq record
                    break
            if last:  # reach EOF before reading enough quality
                yield name, seq, None  # yield a fasta record instead
                break


# The stats generated by this function are based heavily on a program written by Sam Nicholls
# https://github.com/SamStudio8/swell
def calculate_fasta_stats(fasta_path, decimal_places=None):
    if decimal_places is None:
        decimal_places = 5

    with open(fasta_path) as fasta:
        fastas = readfq(fasta)

        num_seqs = 0
        num_bases = 0
        num_acgt = 0
        num_gc = 0
        num_masked = 0
        num_invalid = 0
        num_ambig = 0
        num_ambig_2 = 0
        num_ambig_3 = 0
        current_acgt = 0
        longest_acgt = 0
        current_masked = 0
        longest_masked = 0
        current_invalid = 0
        longest_invalid = 0
        current_ambig = 0
        longest_ambig = 0
        current_gap = 0
        current_ungap = 0
        longest_gap = 0
        longest_ungap = 0

        for name, seq, qual in fastas:
            num_seqs += 1

            for base in seq:
                num_bases += 1

                if base.upper() in "ACGT":
                    num_acgt += 1

                    if base.upper() in "GC":
                        num_gc += 1

                    current_acgt += 1
                    if current_acgt > longest_acgt:
                        longest_acgt = current_acgt

                    current_ungap += 1
                    if current_gap > longest_gap:
                        longest_gap = current_gap

                    current_masked = 0
                    current_invalid = 0
                    current_ambig = 0
                    current_gap = 0

                elif base.upper() in "WSMKRYBDHV":
                    num_ambig += 1

                    if base.upper() in "WSMKRY":
                        num_ambig_2 += 1
                    else:
                        num_ambig_3 += 1

                    current_ambig += 1
                    if current_ambig > longest_ambig:
                        longest_ambig = current_ambig

                    current_ungap += 1
                    if current_gap > longest_gap:
                        longest_gap = current_gap

                    current_acgt = 0
                    current_masked = 0
                    current_invalid = 0
                    current_gap = 0

                elif base.upper() in "NX":
                    num_masked += 1

                    current_masked += 1
                    if current_masked > longest_masked:
                        longest_masked = current_masked

                    current_gap += 1
                    if current_ungap > longest_ungap:
                        longest_ungap = current_ungap

                    current_acgt = 0
                    current_invalid = 0
                    current_ambig = 0
                    current_ungap = 0

                else:
                    num_invalid += 1

                    current_invalid += 1
                    if current_invalid > longest_invalid:
                        longest_invalid = current_invalid

                    current_gap += 1
                    if current_ungap > longest_ungap:
                        longest_ungap = current_ungap

                    current_acgt = 0
                    current_masked = 0
                    current_ambig = 0
                    current_ungap = 0

        pc_acgt = 0
        gc_content = 0
        pc_masked = 0
        pc_invalid = 0
        pc_ambig = 0
        pc_ambig_2 = 0
        pc_ambig_3 = 0

        if num_bases > 0:
            pc_acgt = round(num_acgt / num_bases * 100.0, decimal_places)
            gc_content = round(num_gc / num_bases * 100.0, decimal_places)
            pc_masked = round(num_masked / num_bases * 100.0, decimal_places)
            pc_invalid = round(num_invalid / num_bases * 100.0, decimal_places)
            pc_ambig = round(num_ambig / num_bases * 100.0, decimal_places)
            pc_ambig_2 = round(num_ambig_2 / num_bases * 100.0, decimal_places)
            pc_ambig_3 = round(num_ambig_3 / num_bases * 100.0, decimal_places)
        else:
            pc_invalid = round(100.0, decimal_places)

    return {
        "num_seqs": num_seqs,
        "num_bases": num_bases,
        "pc_acgt": pc_acgt,
        "gc_content": gc_content,
        "pc_masked": pc_masked,
        "pc_invalid": pc_invalid,
        "pc_ambig": pc_ambig,
        "pc_ambig_2": pc_ambig_2,
        "pc_ambig_3": pc_ambig_3,
        "longest_acgt": longest_acgt,
        "longest_masked": longest_masked,
        "longest_invalid": longest_invalid,
        "longest_ambig": longest_ambig,
        "longest_gap": longest_gap,
        "longest_ungap": longest_ungap,
    }


# def calculate_bam_stats(bam_path, decimal_places=None):
#     if decimal_places is None:
#         decimal_places = 5

#     bc = basecount.BaseCount(bam_path, min_base_quality=0, min_mapping_quality=0)

#     pc_coverage = 100 * (len([record["coverage"] for record in bc.records() if record["coverage"] != 0]) / sum(bc.reference_lengths.values()))
#     bam_stats = {
#         "num_reads" : bc.num_reads(),
#         "pc_coverage" : round(pc_coverage, decimal_places),
#         "mean_depth" : round(bc.mean_coverage(), decimal_places),
#         "mean_entropy" : round(bc.mean_entropy(), decimal_places),
#         "vafs" : []
#     }

#     records_gt_100 = [record for record in bc.records() if record["coverage"] >= 100]
#     top_vafs = sorted(records_gt_100, key=lambda d: d["entropy"], reverse=True)[:10]
#     for vaf in top_vafs:
#         bam_stats["vafs"].append(
#             {
#                 "reference" : vaf["reference"],
#                 "position" : vaf["position"],
#                 "depth" : vaf["coverage"],
#                 "num_a" : vaf["num_a"],
#                 "num_c" : vaf["num_c"],
#                 "num_g" : vaf["num_g"],
#                 "num_t" : vaf["num_t"],
#                 "num_ds" : vaf["num_ds"]
#             }
#         )
#     return bam_stats
