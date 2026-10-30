import React, { useState, useEffect, useCallback } from 'react';
import {
  Building2,
  Plus,
  Search,
  MapPin,
  Bed,
  Bath,
  Maximize,
  Edit,
  Trash2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { apiClient, type BackendProperty } from '../../api/client';

export const AgencyPropertiesPage: React.FC = () => {
  const [properties, setProperties] = useState<BackendProperty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProperty, setEditingProperty] = useState<BackendProperty | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    property_type: 'apartment',
    listing_type: 'sale',
    status: 'available',
    price: '',
    currency: 'AED',
    location: '',
    address: '',
    bedrooms: '',
    bathrooms: '',
    area_sqft: '',
    amenities: '',
  });

  const fetchProperties = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.properties.list({
        search: search.trim() || undefined,
        property_type: typeFilter === 'all' ? undefined : typeFilter,
        status: statusFilter === 'all' ? undefined : statusFilter,
        size: 50,
      });
      setProperties(res.items);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch inventory.');
    } finally {
      setLoading(false);
    }
  }, [search, typeFilter, statusFilter]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleOpenModal = (prop?: BackendProperty) => {
    if (prop) {
      setEditingProperty(prop);
      setFormData({
        title: prop.title,
        description: prop.description || '',
        property_type: prop.property_type,
        listing_type: prop.listing_type,
        status: prop.status,
        price: String(prop.price),
        currency: prop.currency,
        location: prop.location,
        address: prop.address || '',
        bedrooms: prop.bedrooms !== null ? String(prop.bedrooms) : '',
        bathrooms: prop.bathrooms !== null ? String(prop.bathrooms) : '',
        area_sqft: prop.area_sqft !== null ? String(prop.area_sqft) : '',
        amenities: prop.amenities.join(', '),
      });
    } else {
      setEditingProperty(null);
      setFormData({
        title: '',
        description: '',
        property_type: 'apartment',
        listing_type: 'sale',
        status: 'available',
        price: '',
        currency: 'AED',
        location: '',
        address: '',
        bedrooms: '2',
        bathrooms: '2',
        area_sqft: '1200',
        amenities: 'Balcony, Central A/C, Covered Parking, Security',
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const payload: any = {
        title: formData.title,
        description: formData.description || null,
        property_type: formData.property_type,
        listing_type: formData.listing_type,
        status: formData.status,
        price: parseFloat(formData.price),
        currency: formData.currency,
        location: formData.location,
        address: formData.address || null,
        bedrooms: formData.bedrooms ? parseInt(formData.bedrooms) : null,
        bathrooms: formData.bathrooms ? parseInt(formData.bathrooms) : null,
        area_sqft: formData.area_sqft ? parseFloat(formData.area_sqft) : null,
        amenities: formData.amenities
          ? formData.amenities.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
      };

      if (editingProperty) {
        const updated = await apiClient.properties.update(editingProperty.id, payload);
        setProperties((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      } else {
        const created = await apiClient.properties.create(payload);
        setProperties((prev) => [created, ...prev]);
      }
      setIsModalOpen(false);
    } catch (err: any) {
      alert(`Error saving listing: ${err?.message || 'Failed'}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this property listing?')) return;
    try {
      await apiClient.properties.delete(id);
      setProperties((prev) => prev.filter((p) => p.id !== id));
    } catch (err: any) {
      alert(`Error deleting listing: ${err?.message || 'Failed'}`);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Building2 className="w-6 h-6 text-indigo-400" />
            Property Inventory
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Manage live properties catalog queried by visitors and autonomous AI agent tools.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchProperties}
            className="p-2.5 bg-zinc-900 border border-white/10 rounded-xl text-zinc-300 hover:text-white transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleOpenModal()}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition"
          >
            <Plus className="w-4 h-4" /> Add Listing
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="relative md:col-span-2">
          <Search className="w-4 h-4 absolute left-3 top-3 text-zinc-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, location, address..."
            className="w-full bg-[#121216] border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-[#121216] border border-white/10 rounded-xl px-3 py-2.5 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Types</option>
          <option value="apartment">Apartment</option>
          <option value="villa">Villa</option>
          <option value="townhouse">Townhouse</option>
          <option value="penthouse">Penthouse</option>
          <option value="commercial">Commercial</option>
          <option value="land">Land</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-[#121216] border border-white/10 rounded-xl px-3 py-2.5 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Statuses</option>
          <option value="available">Available</option>
          <option value="under_offer">Under Offer</option>
          <option value="sold">Sold</option>
          <option value="rented">Rented</option>
        </select>
      </div>

      {/* Grid of Listings */}
      {loading ? (
        <div className="p-16 text-center text-zinc-500 text-sm">Loading property catalog...</div>
      ) : error ? (
        <div className="p-8 text-center text-rose-400 text-sm flex items-center justify-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      ) : properties.length === 0 ? (
        <div className="p-16 text-center text-zinc-500 text-sm border border-dashed border-white/10 rounded-2xl">
          No property listings found. Click "Add Listing" to publish properties to your agency catalog.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {properties.map((prop) => (
            <div
              key={prop.id}
              className="bg-[#0F0F12] border border-white/8 rounded-2xl p-5 space-y-4 hover:border-white/15 transition flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase px-2.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {prop.property_type}
                  </span>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${
                      prop.status === 'available'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-zinc-800 text-zinc-400'
                    }`}
                  >
                    {prop.status.replace('_', ' ')}
                  </span>
                </div>

                <h3 className="font-bold text-base text-white truncate">{prop.title}</h3>

                <div className="text-xl font-extrabold text-white">
                  {prop.currency} {Number(prop.price).toLocaleString()}
                </div>

                <div className="flex items-center gap-1.5 text-xs text-zinc-400 truncate">
                  <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                  <span className="truncate">{prop.location}</span>
                </div>

                <div className="grid grid-cols-3 gap-2 py-2 border-y border-white/5 text-xs text-zinc-300">
                  <div className="flex items-center gap-1">
                    <Bed className="w-3.5 h-3.5 text-zinc-500" />
                    <span>{prop.bedrooms ?? 'Studio'} Beds</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Bath className="w-3.5 h-3.5 text-zinc-500" />
                    <span>{prop.bathrooms ?? 1} Baths</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Maximize className="w-3.5 h-3.5 text-zinc-500" />
                    <span>{prop.area_sqft ? `${prop.area_sqft} sqft` : 'N/A'}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => handleOpenModal(prop)}
                  className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(prop.id)}
                  className="p-2 text-zinc-400 hover:text-rose-400 hover:bg-rose-950/20 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal: Create/Edit Listing */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121216] border border-white/10 rounded-2xl max-w-2xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-white">
              {editingProperty ? 'Edit Property Listing' : 'Add Property to Catalog'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-zinc-400 uppercase">Title</label>
                <input
                  required
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Luxury 3BR Villa in Palm Jumeirah"
                  className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Type</label>
                  <select
                    value={formData.property_type}
                    onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="apartment">Apartment</option>
                    <option value="villa">Villa</option>
                    <option value="townhouse">Townhouse</option>
                    <option value="penthouse">Penthouse</option>
                    <option value="commercial">Commercial</option>
                    <option value="land">Land</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Listing</label>
                  <select
                    value={formData.listing_type}
                    onChange={(e) => setFormData({ ...formData, listing_type: e.target.value })}
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="sale">For Sale</option>
                    <option value="rent">For Rent</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="available">Available</option>
                    <option value="under_offer">Under Offer</option>
                    <option value="sold">Sold</option>
                    <option value="rented">Rented</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Price</label>
                  <input
                    required
                    type="number"
                    step="any"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    placeholder="e.g. 2500000"
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Currency</label>
                  <input
                    required
                    type="text"
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Location / Area</label>
                  <input
                    required
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    placeholder="e.g. Downtown Dubai"
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-400 uppercase">Bedrooms</label>
                  <input
                    type="number"
                    value={formData.bedrooms}
                    onChange={(e) => setFormData({ ...formData, bedrooms: e.target.value })}
                    placeholder="e.g. 3"
                    className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-400 uppercase">Amenities (comma-separated)</label>
                <input
                  type="text"
                  value={formData.amenities}
                  onChange={(e) => setFormData({ ...formData, amenities: e.target.value })}
                  placeholder="Pool, Gym, Balcony, Sea View"
                  className="w-full mt-1 bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-zinc-800 text-zinc-300 rounded-xl text-sm hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition"
                >
                  {submitting ? 'Saving...' : editingProperty ? 'Save Changes' : 'Publish Listing'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

