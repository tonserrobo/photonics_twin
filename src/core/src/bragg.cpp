#include "photonics/bragg.hpp"
#include <complex>
#include <utility>
#include <vector>

namespace photonics {

BraggGrating::BraggGrating(Material high, Material low,
                           real_t centre_nm, std::size_t periods)
    : high_(std::move(high)), low_(std::move(low)),
      centre_nm_(centre_nm), periods_(periods) {
    rebuild_stack_();
}

void BraggGrating::set_centre_nm(real_t v) { centre_nm_ = v; rebuild_stack_(); }
void BraggGrating::set_periods(std::size_t v) { periods_ = v; rebuild_stack_(); }

void BraggGrating::rebuild_stack_() {
    cached_stack_ = LayerStack{};
    const real_t t_h = centre_nm_ / (real_t{4.0} * high_.n(centre_nm_));
    const real_t t_l = centre_nm_ / (real_t{4.0} * low_.n(centre_nm_));
    for (std::size_t i = 0; i < periods_; ++i) {
        cached_stack_.add_layer(t_h, high_);
        cached_stack_.add_layer(t_l, low_);
    }
}

void BraggGrating::reflectance(const real_t* wl, std::size_t n_wl,
                               real_t* R_out) const {
    std::vector<complex_t> r(n_wl), t(n_wl);
    tmm_sweep(cached_stack_, wl, n_wl, r.data(), t.data());
    for (std::size_t i = 0; i < n_wl; ++i) {
        R_out[i] = std::norm(r[i]);
    }
}

}  // namespace photonics
